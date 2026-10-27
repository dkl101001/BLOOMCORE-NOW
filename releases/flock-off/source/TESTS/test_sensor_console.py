import json
import importlib.util
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flockoff.sensor_session import SessionConfig, preflight, run_session, verify_session
from flockoff.sensor_transport import LineFramer, SerialMux, StreamEvent, replay_sources, serial_port

ROOT = Path(__file__).resolve().parents[1]


class FakeSerial:
    def __init__(self, chunks=(), failure=None):
        self.chunks = list(chunks)
        self.failure = failure
        self.closed = False
        self.writes = 0

    def read(self, size):
        if self.chunks: return self.chunks.pop(0)
        if self.failure: raise self.failure
        time.sleep(0.01)
        return b''

    def close(self): self.closed = True
    def write(self, data):
        self.writes += 1
        raise AssertionError('receiver host must not write')


class TransportTests(unittest.TestCase):
    def test_fragmented_utf8_and_crlf(self):
        framer = LineFramer()
        self.assertEqual(framer.feed(b'{"v":"\xc3'), [])
        self.assertEqual(framer.feed(b'\xa9"}\r\n\n'), ['{"v":"é"}'])
        self.assertEqual(framer.feed(b'{"last":1}'), [])
        self.assertEqual(framer.finish(), ['{"last":1}'])

    def test_line_limits_apply_with_and_without_newline(self):
        for payload in (b'123456', b'123456\n'):
            with self.assertRaises(ValueError): LineFramer(5).feed(payload)
        with self.assertRaises(UnicodeDecodeError): LineFramer().feed(b'\xff\n')

    def test_serial_urls_and_path_escape_refused(self):
        for endpoint in ('socket://host:9', 'serial:rfc2217://host', 'serial:/dev/../etc/passwd', 'file.txt', 'serial:COM0'):
            with self.assertRaises(ValueError): serial_port(endpoint)
        self.assertEqual(serial_port('serial:COM14'), 'COM14')

    def test_silence_is_visible_and_cancel_closes_without_write(self):
        fake = FakeSerial([b'{"event":"config"}\n'])
        mux = SerialMux({'sensor': 'serial:COM4'}, silence_seconds=0.03,
                        factory=lambda *args: fake)
        events = []
        iterator = iter(mux)
        try:
            for event in iterator:
                events.append(event)
                if event.state == 'SILENT': break
        finally:
            iterator.close()
        self.assertEqual([e.state for e in events], ['CONNECTED', 'DATA', 'SILENT'])
        self.assertTrue(fake.closed)
        self.assertEqual(fake.writes, 0)
        self.assertTrue(all(not t.is_alive() for t in mux.threads))

    def test_disconnect_stops_all_sources(self):
        first, second = FakeSerial(failure=OSError('unplugged')), FakeSerial()
        mux = SerialMux({'sensor': 'serial:COM4', 'pose': 'serial:COM5'},
                        factory=lambda endpoint, baud: first if endpoint.endswith('4') else second)
        events = list(mux)
        self.assertIn('FAILED', [e.state for e in events])
        self.assertTrue(first.closed and second.closed)

    def test_cancel_when_queue_is_full(self):
        fake = FakeSerial([b'{}\n' * 100])
        mux = SerialMux({'sensor': 'serial:COM4'}, queue_size=1, factory=lambda *args: fake)
        iterator = iter(mux); next(iterator)
        time.sleep(0.03)
        iterator.close()
        self.assertTrue(fake.closed)
        self.assertTrue(all(not t.is_alive() for t in mux.threads))

    @unittest.skipUnless(importlib.util.find_spec('serial'), 'optional pyserial dependency')
    def test_serial_open_sets_read_timeout_and_never_writes(self):
        import serial
        class Port:
            def __init__(self, **kwargs):
                self.args = kwargs; self.opened = False
            def open(self):
                self.opened = True
                assert self.dtr is False and self.rts is False
            def close(self): pass
        from flockoff.sensor_transport import open_serial
        with patch.object(serial, 'Serial', Port):
            port = open_serial('serial:COM14', 115200)
        self.assertTrue(port.opened)
        self.assertEqual(port.args['timeout'], 0.2)
        self.assertFalse(port.args['xonxoff'])


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sensor = self.root / 'sensor.ndjson'
        self.pose = self.root / 'pose.ndjson'
        self.output, self.key = self.root / 'session', self.root / 'secret.key'
        self.config = SessionConfig('REPLAY', 'remote_id', str(self.sensor), 'rid-rx-1',
                                    'SYNTHETIC_RECEIVER', pose_input=str(self.pose), core_build='SYNTHETIC_DECODER')
        rows = [json.loads(line) for line in (ROOT / 'TESTS/synthetic_traces/remote_id_mobile.ndjson').read_text().splitlines()]
        rows[-1]['observed_at_utc'] = '2026-08-23T12:00:03Z'
        self.sensor.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.pose.write_bytes((ROOT / 'TESTS/fixtures/remote_id_observer_pose.ndjson').read_bytes())

    def tearDown(self): self.tmp.cleanup()

    def run_case(self, **kwargs):
        return run_session(self.config, self.output, self.key, **kwargs)

    def test_replay_order_and_preserved_time(self):
        events = list(replay_sources(self.sensor, self.pose))
        self.assertEqual([e.source for e in events], ['pose', 'sensor', 'pose', 'sensor', 'sensor'])
        self.assertEqual(events[0].at, '2026-08-23T12:00:00Z')

    def test_missing_or_backwards_replay_time_refused(self):
        for text in ('{"event":"receiver_status"}\n',
                     '{"observed_at_utc":"2026-01-02T00:00:00Z"}\n{"observed_at_utc":"2026-01-01T00:00:00Z"}\n'):
            self.sensor.write_text(text)
            with self.assertRaises(ValueError): list(replay_sources(self.sensor))

    def test_end_to_end_remote_id_custody_and_verification(self):
        result = self.run_case()
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['hardware_validation'], 'NOT_RUN')
        self.assertGreater(result['stored_nodes'], 0)
        self.assertEqual(result['stored_poses'], 2)
        self.assertEqual(verify_session(self.output, self.key)['state'], 'VERIFIED_BYTES')
        self.assertEqual(verify_session(self.output, self.key)['restricted_poses_decrypted'], 2)
        diagnostics = (self.output / 'events.ndjson').read_text()
        self.assertNotIn('SYNTHETIC-RID-0001', diagnostics)
        self.assertNotIn('latitude', diagnostics)
        self.assertNotIn('longitude', diagnostics)
        self.assertFalse((self.output / 'secret.key').exists())
        connection = sqlite3.connect(self.output / 'evidence.sqlite')
        try:
            stored = [json.loads(r[0]) for r in connection.execute("SELECT canonical_json FROM ledger_events WHERE event_kind='observation'")]
            self.assertEqual(sorted(row['observed_at_utc'] for row in stored),
                             ['2026-08-23T12:00:01Z', '2026-08-23T12:00:02Z'])
        finally: connection.close()

    def test_corruption_and_wrong_key_detected(self):
        self.run_case()
        wrong = self.root / 'wrong.key'
        data = json.loads(self.key.read_text()); data['rotation_secret_hex'] = '00' * 32
        wrong.write_text(json.dumps(data))
        with self.assertRaises(ValueError): verify_session(self.output, wrong)
        with (self.output / 'events.ndjson').open('ab') as stream: stream.write(b'altered')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'): verify_session(self.output, self.key)

    def test_empty_input_is_not_successful_detection(self):
        self.sensor.write_text('')
        result = self.run_case()
        self.assertEqual(result['status'], 'NO_USABLE_SENSOR_RECORDS')
        self.assertFalse(result['absence_claim_permitted'])

    def test_malformed_replay_seals_failed_session(self):
        self.sensor.write_text('not json\n')
        result = self.run_case()
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(verify_session(self.output, self.key)['session_status'], 'FAILED')

    def test_live_mode_refuses_files(self):
        self.config.mode = 'LIVE_SERIAL'
        self.assertFalse(preflight(self.config)['ready'])

    def test_new_session_never_overwrites_or_colocates_key(self):
        with self.assertRaises(ValueError): run_session(self.config, self.output, self.output / 'key')
        self.run_case()
        with self.assertRaises(FileExistsError): self.run_case()

    def test_stop_before_replay_is_recorded(self):
        stop = threading.Event(); stop.set()
        self.assertEqual(self.run_case(stop=stop)['status'], 'STOPPED')

    def test_record_limit_produces_incomplete_capture_state(self):
        self.config.max_records = 1
        result = self.run_case()
        self.assertEqual(result['status'], 'LIMIT_REACHED')
        self.assertEqual(result['counts'].get('sensor_records', 0), 0)
        self.assertEqual(verify_session(self.output, self.key)['session_status'], 'LIMIT_REACHED')

    def test_live_transport_failure_is_not_success(self):
        self.config.mode = 'LIVE_SERIAL'; self.config.sensor_input = 'serial:COM4'; self.config.pose_input = ''
        class FailedMux:
            def __init__(self, *args, **kwargs): pass
            def __iter__(self):
                yield StreamEvent('sensor', 'FAILED', '2026-10-27T00:00:00Z', detail='SerialException')
        with patch('flockoff.sensor_session.list_ports', return_value={'serial_dependency': True, 'ports': []}):
            result = self.run_case(mux_factory=FailedMux)
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['absence_claim_permitted'])

    def test_live_invalid_payload_quarantined_then_stop(self):
        self.config.mode = 'LIVE_SERIAL'; self.config.sensor_input = 'serial:COM4'; self.config.pose_input = ''
        class InputMux:
            def __init__(self, *args, **kwargs): self.stop = kwargs['stop']
            def __iter__(self):
                yield StreamEvent('sensor', 'DATA', '2026-10-27T00:00:00Z', '{broken secret_identifier')
                self.stop.set()
        with patch('flockoff.sensor_session.list_ports', return_value={'serial_dependency': True, 'ports': []}):
            result = self.run_case(mux_factory=InputMux)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['counts']['quarantined'], 1)
        self.assertNotIn('secret_identifier', (self.output / 'events.ndjson').read_text())

    def test_flock_you_pipeline_creates_nodes_from_explicit_passes(self):
        records = [json.loads(line) for line in (ROOT / 'TESTS/synthetic_traces/fixed_two_pass.jsonl').read_text().splitlines()]
        passes = {row['pose_alias']: row['pass_id'] for row in records if row['kind'] != 'pose'}
        poses, detections = [], []
        for row in records:
            if row['kind'] == 'pose':
                row['pass_id'] = passes[row['alias']]; poses.append(row)
            else: detections.append({'received_at_utc': row['observed_at_utc'], 'payload': row['payload']})
        self.sensor.write_text(''.join(json.dumps(row) + '\n' for row in detections))
        self.pose.write_text(''.join(json.dumps(row) + '\n' for row in poses))
        self.config.protocol = 'flock_you'; self.config.receiver_id = poses[0]['receiver_id']
        self.config.signature = str(ROOT / 'SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json')
        result = self.run_case()
        self.assertEqual(result['status'], 'COMPLETED', result)
        self.assertGreater(result['stored_nodes'], 0)
        self.assertEqual(verify_session(self.output, self.key)['state'], 'VERIFIED_BYTES')


if __name__ == '__main__': unittest.main()
