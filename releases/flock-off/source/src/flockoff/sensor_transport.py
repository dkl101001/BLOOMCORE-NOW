"""Bounded read-only host transport. Never opens serial URL handlers or writes bytes."""
from __future__ import annotations

import datetime as dt
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

MAX_LINE_BYTES = 1_048_576


def utc_now():
    return dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z')


@dataclass(frozen=True)
class StreamEvent:
    source: str
    state: str
    at: str
    line: str | None = None
    detail: str | None = None


class LineFramer:
    def __init__(self, limit=MAX_LINE_BYTES):
        self.buffer = bytearray()
        self.limit = limit

    def feed(self, chunk):
        self.buffer.extend(chunk)
        lines = []
        while b'\n' in self.buffer:
            raw, _, self.buffer = self.buffer.partition(b'\n')
            if len(raw) > self.limit:
                raise ValueError('NDJSON line exceeds configured limit')
            line = raw.decode('utf-8', errors='strict').rstrip('\r')
            if line.strip(): lines.append(line)
        if len(self.buffer) > self.limit:
            raise ValueError('NDJSON line exceeds configured limit')
        return lines

    def finish(self):
        return self.feed(b'\n') if self.buffer else []


def serial_port(endpoint):
    if not isinstance(endpoint, str) or not endpoint.startswith('serial:'):
        raise ValueError('live inputs must be explicit serial:COM3 or serial:/dev/ttyACM0 endpoints')
    port = endpoint[len('serial:'):]
    if not (re.fullmatch(r'COM[1-9][0-9]*', port, re.I) or re.fullmatch(r'/dev/[A-Za-z0-9_./-]+', port)):
        raise ValueError('only local COM or /dev serial devices are supported; URLs are refused')
    if '..' in port.split('/'):
        raise ValueError('invalid serial device path')
    return port


def open_serial(endpoint, baud):
    port = serial_port(endpoint)
    try:
        from serial import Serial
    except ImportError as exc:
        raise RuntimeError('Install the optional serial dependency: pip install pyserial==3.5') from exc
    # Construct closed so control-line preferences precede open. Some drivers can
    # still pulse lines on open; this must be checked on the actual receiver.
    stream = Serial(port=None, baudrate=baud, timeout=0.2, xonxoff=False,
                    rtscts=False, dsrdtr=False, write_timeout=0)
    stream.dtr = False
    stream.rts = False
    stream.port = port
    try:
        stream.open()
    except Exception:
        stream.close()
        raise
    return stream


def list_ports():
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        return {'serial_dependency': False, 'ports': []}
    return {'serial_dependency': True, 'ports': [
        {'device': p.device, 'description': p.description, 'vid': p.vid, 'pid': p.pid}
        for p in comports()]}


class SerialMux:
    """Finite queue, timed reads, explicit silence, cancellation and disconnects."""
    def __init__(self, endpoints, *, baud=115200, pose_baud=9600, stop=None,
                 silence_seconds=5.0, queue_size=128, factory=open_serial):
        if not endpoints or 'sensor' not in endpoints:
            raise ValueError('a sensor endpoint is required')
        if set(endpoints) - {'sensor', 'pose'}:
            raise ValueError('unknown source name')
        if len(set(endpoints.values())) != len(endpoints):
            raise ValueError('sensor and pose must use different devices')
        for endpoint in endpoints.values(): serial_port(endpoint)
        if baud <= 0 or pose_baud <= 0 or silence_seconds <= 0 or queue_size < 1:
            raise ValueError('baud, silence interval and queue size must be positive')
        self.endpoints, self.baud, self.pose_baud = endpoints, baud, pose_baud
        self.stop = stop if stop is not None else threading.Event()
        self.silence = silence_seconds
        self.items = queue.Queue(maxsize=queue_size)
        self.factory = factory
        self.threads = []

    def put(self, item):
        while not self.stop.is_set():
            try:
                self.items.put(item, timeout=0.1)
                return
            except queue.Full:
                continue  # Backpressure; no host-side record dropping.

    def reader(self, source, endpoint):
        stream = None
        try:
            stream = self.factory(endpoint, self.pose_baud if source == 'pose' else self.baud)
            self.put(StreamEvent(source, 'CONNECTED', utc_now()))
            framer = LineFramer()
            last_record = time.monotonic()
            silent = False
            while not self.stop.is_set():
                chunk = stream.read(4096)
                if chunk:
                    for line in framer.feed(chunk):
                        last_record = time.monotonic()
                        silent = False
                        self.put(StreamEvent(source, 'DATA', utc_now(), line))
                if not silent and time.monotonic() - last_record >= self.silence:
                    self.put(StreamEvent(source, 'SILENT', utc_now(), detail='No complete record; RF absence is not established.'))
                    silent = True
        except Exception as exc:
            # Never put raw lines/identifiers into diagnostic logs.
            self.put(StreamEvent(source, 'FAILED', utc_now(), detail=type(exc).__name__))
        finally:
            if stream is not None:
                stream.close()
            self.put(StreamEvent(source, 'CLOSED', utc_now()))

    def __iter__(self):
        self.threads = [threading.Thread(target=self.reader, args=(name, endpoint), daemon=True,
                                        name=f'sensor-reader-{name}') for name, endpoint in self.endpoints.items()]
        for thread in self.threads: thread.start()
        try:
            while not self.stop.is_set():
                try:
                    event = self.items.get(timeout=0.2)
                except queue.Empty:
                    continue
                yield event
                if event.state in ('FAILED', 'CLOSED'):
                    return  # Require an explicit new session after a source fails.
        finally:
            self.stop.set()
            for thread in self.threads: thread.join(timeout=2)
            if any(thread.is_alive() for thread in self.threads):
                raise RuntimeError('serial driver did not stop within the shutdown bound')


def replay_sources(sensor_path, pose_path=None, *, stop=None):
    """Merge two ordered files by recorded time, poses first on ties; never wall-clock restamp."""
    from .live import strict_json_object
    stop = stop if stop is not None else threading.Event()
    def rows(source, path):
        previous = None
        with Path(path).open('rb') as stream:
            while not stop.is_set():
                raw = stream.readline(MAX_LINE_BYTES + 1)
                if not raw: break
                if len(raw) > MAX_LINE_BYTES: raise ValueError('replay line exceeds 1 MiB')
                if not raw.strip(): continue
                line = raw.decode('utf-8')
                value = strict_json_object(line)
                stamp = value.get('received_at_utc', value.get('observed_at_utc'))
                if stamp is None:
                    raise ValueError('replay records require received_at_utc or observed_at_utc; no invented timestamp')
                instant = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                if instant.utcoffset() is None: raise ValueError('replay timestamp requires timezone')
                if previous is not None and instant < previous: raise ValueError('replay source timestamps are out of order')
                previous = instant
                yield instant, StreamEvent(source, 'DATA', stamp, line)
    streams = {'sensor': rows('sensor', sensor_path)}
    if pose_path: streams['pose'] = rows('pose', pose_path)
    heads = {}
    try:
        for source, stream in streams.items():
            heads[source] = next(stream, None)
        while any(heads.values()) and not stop.is_set():
            source = min((s for s in heads if heads[s] is not None),
                         key=lambda s: (heads[s][0], 0 if s == 'pose' else 1))
            yield heads[source][1]
            heads[source] = next(streams[source], None)
    finally:
        for stream in streams.values(): stream.close()
