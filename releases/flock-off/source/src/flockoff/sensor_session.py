"""Managed sensor sessions with explicit replay/live provenance and sealed closeout."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import threading
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from . import runtime_source_digest
from .canonical import canonical_bytes, keyed_digest
from .cli import PACKAGE_ROOT, _load_json, _validated_signature
from .crypto import FieldCipher, EncryptedRecord
from .ledger import EvidenceLedger
from .live import LiveRealityLoop, TargetExpectation, strict_json_object
from .live_remote_id import RemoteIDLiveLoop
from .sensor_transport import SerialMux, list_ports, replay_sources, serial_port, utc_now
from flockoff_red_tape.ledger import private_write, windows_user_sid


@dataclass
class SessionConfig:
    mode: str
    protocol: str
    sensor_input: str
    receiver_id: str
    receiver_build: str
    pose_input: str = ''
    baud: int = 115200
    pose_baud: int = 9600
    core_build: str = ''
    signature: str = ''
    targets: str = ''
    max_records: int = 10000
    max_seconds: int = 3600


def preflight(config):
    errors, notes = [], []
    if config.mode not in ('REPLAY', 'LIVE_SERIAL'): errors.append('Select REPLAY or LIVE_SERIAL.')
    if config.protocol not in ('flock_you', 'remote_id'): errors.append('Unsupported protocol.')
    for name in ('receiver_id', 'receiver_build'):
        if not getattr(config, name).strip(): errors.append(f'{name} must be recorded explicitly.')
    if config.protocol == 'remote_id' and not config.core_build.strip():
        errors.append('Remote ID requires the actual external decoder build reference.')
    if not 1 <= config.baud <= 4_000_000 or not 1 <= config.pose_baud <= 4_000_000:
        errors.append('Serial baud must be 1..4000000.')
    if not 1 <= config.max_records <= 100000 or not 1 <= config.max_seconds <= 86400:
        errors.append('Session limits must be 1..100000 records and 1..86400 seconds.')
    if config.sensor_input == config.pose_input:
        errors.append('Sensor and pose inputs must be distinct.')
    if config.mode == 'LIVE_SERIAL':
        for path in (config.sensor_input, config.pose_input):
            if path:
                try: serial_port(path)
                except ValueError as exc: errors.append(str(exc))
        if not config.sensor_input: errors.append('A live sensor endpoint is required.')
        if not list_ports()['serial_dependency']: errors.append('pyserial==3.5 is not installed in this Python environment.')
        notes.append('Opening a serial port may change USB control lines. Radio firmware receive-only behavior is not verified by host code.')
    elif config.mode == 'REPLAY':
        for path in (config.sensor_input, config.pose_input):
            if path and not Path(path).is_file(): errors.append('Replay input file is missing.')
        if not config.sensor_input: errors.append('A timestamped replay file is required.')
        notes.append('Replay uses recorded timestamps and never counts as hardware validation.')
    if config.protocol == 'flock_you':
        try: _validated_signature(Path(config.signature))
        except (ValueError, OSError, KeyError): errors.append('Select a valid, hash-verified signature file.')
    if config.targets:
        try:
            doc = _load_json(Path(config.targets))
            if not isinstance(doc.get('targets'), list): raise ValueError('targets must be an array')
            for item in doc['targets']: TargetExpectation.from_dict(item)
        except (ValueError, OSError, KeyError, TypeError): errors.append('Target expectation file is invalid.')
    if not config.pose_input: notes.append('No observer pose input: RF localization is unavailable; no observer position is invented.')
    notes += ['Serial continuity does not prove channel coverage or absence.',
              'Signatures are candidate assertions, not calibrated identification probabilities.',
              'Session output is private. Full-disk/database encryption is not provided by this console.']
    return {'ready': not errors, 'errors': errors, 'notes': notes,
            'hardware_validation': 'NOT_RUN', 'absence_claim_permitted': False}


def protect_directory(path):
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name == 'nt':
        subprocess.run(['icacls.exe', str(path), '/inheritance:r', '/grant:r',
                        '*' + windows_user_sid() + ':(OI)(CI)F'],
                       capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def evidence_summary(item):
    """Allowlisted operator facts; no raw emitter IDs, observer route or free text."""
    value = item.get('value', {})
    result = {k: value[k] for k in ('match_state', 'claim_ceiling', 'calibration_state',
                                   'claim_level', 'state', 'basis')
              if k in value and isinstance(value[k], (str, bool, int, float))}
    if item['kind'] == 'observation':
        measurement = value.get('measurement', {})
        for key in ('rssi_dbm', 'channel', 'frequency_mhz'):
            if isinstance(measurement.get(key), (int, float)): result[key] = measurement[key]
    if item.get('alert') == 'COMPATIBLE_FLOCK_YOU_SIGNATURE':
        result['alert'] = item['alert']
        result['claim_ceiling'] = item['claim_ceiling']
    return result


def run_session(config, output, key_path, *, stop=None, notify=None, mux_factory=SerialMux):
    """Create one immutable session directory. External key never goes in that directory."""
    checked = preflight(config)
    if not checked['ready']: raise ValueError('\n'.join(checked['errors']))
    output, key_path = Path(output).resolve(), Path(key_path).resolve()
    if key_path == output or output in key_path.parents:
        raise ValueError('Keep the session key outside the session directory.')
    if output.exists() or key_path.exists(): raise FileExistsError('Session output and key must both be new.')
    stop = stop if stop is not None else threading.Event()
    notify = notify or (lambda item: None)
    session_id = uuid.uuid4().hex
    secret, route_key = os.urandom(32), os.urandom(32)
    private_write(key_path, canonical_bytes({'session_id': session_id, 'rotation_secret_hex': secret.hex(),
                                          'route_key_base64': base64.b64encode(route_key).decode()}))
    protect_directory(output)
    cipher = FieldCipher(route_key)
    encrypted = cipher.encrypt(asdict(config), session_id)
    private_write(output / 'config.encrypted.json', canonical_bytes({
        'key_id': encrypted.key_id, 'nonce': base64.b64encode(encrypted.nonce).decode(),
        'ciphertext': base64.b64encode(encrypted.ciphertext).decode()}))
    private_write(output / 'events.ndjson', b'')
    private_write(output / 'evidence.sqlite', b'')
    counters = Counter()
    summary = {'format': 'flockoff-session-v1', 'session_id': session_id, 'mode': config.mode,
               'protocol': config.protocol, 'started_at': utc_now(), 'status': 'RUNNING',
               'hardware_validation': 'NOT_RUN', 'absence_claim_permitted': False,
               'code_digest': runtime_source_digest(), 'receiver_build': config.receiver_build,
               'decoder_build': config.core_build, 'source_inputs_persisted': False}
    # The start marker survives process death; absence of a sealed receipt means incomplete.
    private_write(output / 'started.json', canonical_bytes(summary))
    stream = None
    last_at = None
    limit_hit = threading.Event()
    def time_limit():
        limit_hit.set(); stop.set()
    timer = threading.Timer(config.max_seconds, time_limit)
    timer.daemon = True
    with (output / 'events.ndjson').open('ab', buffering=0) as log:
        def event(kind, **values):
            item = {'kind': kind, 'at': utc_now(), **values}
            log.write(canonical_bytes(item) + b'\n')
            notify(item)
        timer.start()
        try:
            with EvidenceLedger(output / 'evidence.sqlite', PACKAGE_ROOT / 'SCHEMAS/migrations/0001_initial.sql',
                                cipher, evidence_digest_secret=secret) as ledger:
                common = dict(receiver_id=config.receiver_id, rotation_epoch=session_id,
                              rotation_secret=secret, ledger=ledger, session_id=session_id)
                if config.protocol == 'flock_you':
                    signature = _validated_signature(Path(config.signature))
                    targets = [_ for _ in _load_json(Path(config.targets))['targets']] if config.targets else []
                    loop = LiveRealityLoop(signature=signature,
                        expectations=[TargetExpectation.from_dict(t) for t in targets],
                        hardware_profile_id='xiao-esp32s3-flock-you-2g4',
                        upstream_build_ref=config.receiver_build, **common)
                else:
                    loop = RemoteIDLiveLoop(hardware_profile_id='remote-id-operator-declared',
                        upstream_receiver_revision=config.receiver_build,
                        upstream_core_revision=config.core_build, **common)
                if config.mode == 'REPLAY':
                    stream = replay_sources(config.sensor_input, config.pose_input or None, stop=stop)
                else:
                    endpoints = {'sensor': config.sensor_input}
                    if config.pose_input: endpoints['pose'] = config.pose_input
                    stream = iter(mux_factory(endpoints, baud=config.baud, pose_baud=config.pose_baud, stop=stop))
                event('session_started', mode=config.mode, hardware_validation='NOT_RUN')
                try:
                    for item in stream:
                        if stop.is_set(): break
                        if item.state != 'DATA':
                            event('transport', source=item.source, state=item.state, detail=item.detail)
                            if item.state in ('FAILED', 'CLOSED'): raise RuntimeError('input transport failed or closed')
                            continue
                        last_at = item.at
                        if counters['sensor_records'] + counters['pose_records'] >= config.max_records:
                            limit_hit.set(); stop.set(); break
                        counters[item.source + '_records'] += 1
                        try:
                            payload = strict_json_object(item.line)
                            if 'payload' in payload:
                                if config.mode != 'REPLAY': raise ValueError('live streams require raw decoded events')
                                payload = payload['payload']
                                if not isinstance(payload, dict): raise ValueError('payload must be an object')
                            if item.source == 'pose':
                                generated = loop.ingest_pose(payload)
                            elif config.protocol == 'flock_you':
                                generated = loop.ingest_flock_you(payload, received_at_utc=item.at, host_monotonic_ns=time.monotonic_ns())
                            elif payload.get('event') == 'receiver_status':
                                generated = loop.ingest_status(payload, received_at_utc=item.at)
                            elif payload.get('event') in ('remote_id', 'remote_id_message'):
                                generated = loop.ingest_remote_id(payload, received_at_utc=item.at, host_monotonic_ns=time.monotonic_ns())
                            else:
                                raise ValueError('unsupported decoded event')
                        except (ValueError, KeyError, TypeError) as exc:
                            counters['quarantined'] += 1
                            if item.source == 'sensor': loop.mark_quarantined()
                            event('quarantined', source=item.source, reason=type(exc).__name__,
                                  note='Record rejected; raw input is not retained in diagnostics.')
                            continue
                        counters[item.source + '_accepted'] += 1
                        for generated_item in generated:
                            kind = generated_item['kind']
                            counters[kind] += 1
                            event('evidence', evidence_kind=kind, source=item.source, summary=evidence_summary(generated_item))
                    for generated_item in loop.flush(last_at):
                        counters[generated_item['kind']] += 1
                        event('evidence', evidence_kind=generated_item['kind'], source='finalize')
                    summary['status'] = 'LIMIT_REACHED' if limit_hit.is_set() else ('STOPPED' if stop.is_set() else 'COMPLETED')
                    if not counters['sensor_accepted'] and summary['status'] == 'COMPLETED':
                        summary['status'] = 'NO_USABLE_SENSOR_RECORDS'
                    elif counters['quarantined'] and summary['status'] == 'COMPLETED':
                        summary['status'] = 'COMPLETED_WITH_REJECTIONS'
                finally:
                    if stream is not None: stream.close()
                summary['stored_events'] = ledger.connection.execute('SELECT count(*) FROM ledger_events').fetchone()[0]
                summary['stored_nodes'] = ledger.connection.execute('SELECT count(*) FROM node_revisions').fetchone()[0]
                summary['stored_poses'] = ledger.connection.execute('SELECT count(*) FROM restricted_pose_ciphertexts').fetchone()[0]
        except Exception as exc:
            summary['status'] = 'FAILED'
            summary['failure_type'] = type(exc).__name__
            event('session_failure', reason=type(exc).__name__)
        finally:
            timer.cancel()
        summary['counts'] = dict(counters)
        summary['ended_at'] = utc_now()
        event('session_finished', status=summary['status'], counts=dict(counters))
        os.fsync(log.fileno())
    summary['files'] = {name: hash_file(output / name) for name in
                        ('evidence.sqlite', 'events.ndjson', 'config.encrypted.json', 'started.json')}
    summary['hmac_sha256'] = hmac.digest(secret, canonical_bytes(summary), 'sha256').hex()
    private_write(output / 'receipt.json', canonical_bytes(summary))
    return summary


def verify_session(directory, key_path):
    directory = Path(directory)
    key = _load_json(Path(key_path))
    receipt = _load_json(directory / 'receipt.json')
    body = {k: v for k, v in receipt.items() if k != 'hmac_sha256'}
    expected = hmac.digest(bytes.fromhex(key['rotation_secret_hex']), canonical_bytes(body), 'sha256').hex()
    if key['session_id'] != receipt['session_id'] or not hmac.compare_digest(expected, receipt['hmac_sha256']):
        raise ValueError('wrong key or altered session receipt')
    if set(receipt['files']) != {'evidence.sqlite', 'events.ndjson', 'config.encrypted.json', 'started.json'}:
        raise ValueError('unexpected session file manifest')
    for name, digest in receipt['files'].items():
        if hash_file(directory / name) != digest: raise ValueError('session file digest mismatch: ' + name)
    cipher = FieldCipher.from_base64(key['route_key_base64'])
    encrypted = _load_json(directory / 'config.encrypted.json')
    cipher.decrypt(EncryptedRecord(encrypted['key_id'], base64.b64decode(encrypted['nonce']),
                                   base64.b64decode(encrypted['ciphertext'])), receipt['session_id'])
    connection = sqlite3.connect((directory / 'evidence.sqlite').as_uri() + '?mode=ro', uri=True)
    poses = 0
    try:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name='restricted_pose_ciphertexts'").fetchone():
            for pose_id, key_id, nonce, ciphertext, digest in connection.execute(
                    'SELECT pose_id,key_id,nonce,ciphertext,content_hash FROM restricted_pose_ciphertexts'):
                pose = json.loads(cipher.decrypt(EncryptedRecord(key_id, nonce, ciphertext), pose_id))
                if keyed_digest(bytes.fromhex(key['rotation_secret_hex']), 'restricted-pose-receipt', pose) != digest:
                    raise ValueError('restricted pose custody digest mismatch')
                poses += 1
    finally:
        connection.close()
    return {'state': 'VERIFIED_BYTES', 'session_status': receipt['status'],
            'mode': receipt['mode'], 'hardware_validation': 'NOT_RUN',
            'config_authenticated': True, 'restricted_poses_decrypted': poses}
