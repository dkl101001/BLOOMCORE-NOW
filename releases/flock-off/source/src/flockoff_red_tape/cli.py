# SPDX-License-Identifier: Apache-2.0
"""Local-only command interface. All outputs are drafts until separately reviewed."""

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from .ledger import Ledger, private_write
from .model import Invalid, REVIEW_CHECKS, ready_errors, validate
from .render import packet, request_draft, timing


def strict_load(path):
    path = Path(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise Invalid('input exceeds 8 MiB limit')

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise Invalid('duplicate JSON key')
            result[k] = v
        return result

    def constant(value):
        raise Invalid('non-finite JSON value')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def now():
    return datetime.now(timezone.utc).isoformat()


def parser():
    p = argparse.ArgumentParser(prog='flockoff red-tape', description='Red Tape Dispenser — local accountability packets')
    p.add_argument('--db', type=Path, required=True, help='separate encrypted accountability SQLite store')
    p.add_argument('--key', type=Path, required=True, help='separate private encryption key; back up securely')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='create a new store and random key; never overwrite')
    imp = sub.add_parser('import', help='validate and append a case JSON snapshot')
    imp.add_argument('input', type=Path)
    imp.add_argument('--expected-revision', required=True, type=int)
    for name in ('check', 'review', 'dispense', 'verify', 'verify-packet', 'request', 'answer', 'checkout', 'attach', 'document'):
        s = sub.add_parser(name)
        s.add_argument('case_id')
        if name == 'review':
            s.add_argument('--reviewer', required=True)
            s.add_argument('--attest-premises', action='store_true', required=True)
            s.add_argument('--attest-contrary-evidence', action='store_true', required=True)
            s.add_argument('--attest-meeting-rules', action='store_true', required=True)
        if name == 'dispense':
            s.add_argument('--output', type=Path, required=True, help='new private draft directory')
            s.add_argument('--as-of', required=True, help='YYYY-MM-DD, explicit for reproducibility')
            s.add_argument('--humor', action='store_true')
            s.add_argument('--ready', action='store_true', help='refuse unreviewed or oversized brief')
        if name == 'request':
            s.add_argument('request_id')
            s.add_argument('--follow-up', action='store_true')
            s.add_argument('--output', type=Path, required=True)
        if name == 'answer':
            s.add_argument('input', type=Path, help='one reviewed answer JSON; appended, never substituted')
        if name == 'checkout':
            s.add_argument('--revision', type=int)
            s.add_argument('--output', type=Path, required=True, help='restricted plaintext editing copy')
        if name == 'verify-packet':
            s.add_argument('--directory', type=Path, required=True)
        if name in ('attach', 'document'):
            s.add_argument('source_id')
            if name == 'attach':
                s.add_argument('input', type=Path, help='existing public document to retain encrypted, up to 20 MiB')
            else:
                s.add_argument('--output', required=True, type=Path)
    approve = sub.add_parser('approve', help='approve exact reviewed artifact bytes for local public export')
    approve.add_argument('candidate', type=Path)
    approve.add_argument('--reviewer', required=True)
    approve.add_argument('--attest-redactions-and-consent', action='store_true', required=True)
    exp = sub.add_parser('export', help='copy approved bytes locally; does not publish')
    exp.add_argument('candidate', type=Path)
    exp.add_argument('--output', required=True, type=Path)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        with Ledger(args.db, args.key, create=args.command == 'init') as store:
            if args.command == 'init':
                result = {'state': 'initialized', 'encrypted_payloads': True, 'external_key_required': True}
            elif args.command == 'import':
                result = store.append(strict_load(args.input), args.expected_revision)
            elif args.command == 'approve':
                result = store.approve_artifact(args.candidate.read_bytes(), args.reviewer, now(), args.attest_redactions_and_consent)
            elif args.command == 'export':
                result = store.export_approved(args.candidate.read_bytes(), args.output)
            else:
                case, receipt = store.load(args.case_id, getattr(args, 'revision', None))
                if args.command in ('attach', 'document'):
                    source = next((s for s in case['sources'] if s['id'] == args.source_id), None)
                    if source is None:
                        raise Invalid('source not found')
                    if args.command == 'attach':
                        if args.input.stat().st_size > 20 * 1024 * 1024:
                            raise Invalid('document exceeds 20 MiB limit')
                        data = args.input.read_bytes()
                        sha = hashlib.sha256(data).hexdigest()
                        if source.get('sha256') and source['sha256'] != sha:
                            raise Invalid('document differs from the declared source hash; add a new source instead')
                        source['sha256'] = sha
                        case.pop('review', None)
                        result = store.append(case, receipt['revision'], {sha: data})
                    else:
                        private_write(args.output, store.read_document(source.get('sha256')))
                        result = {'state': 'restricted_document_copy'}
                elif args.command == 'verify':
                    count, _ = store.verify(args.case_id)
                    result = {'state': 'verified', 'revisions': count, 'receipt': receipt,
                              'limitation': 'Detects modification and internal gaps, not deletion of the latest suffix without an external checkpoint.'}
                elif args.command == 'verify-packet':
                    manifest = strict_load(args.directory / 'packet_receipt.json')
                    case, original = store.load(args.case_id, manifest['revision_receipt']['revision'])
                    if manifest['revision_receipt'] != original:
                        raise Invalid('packet revision does not match ledger custody')
                    expected = packet(case, original, manifest['as_of'], manifest['humor'])
                    actual_names = {p.name for p in args.directory.iterdir()}
                    if actual_names != set(expected):
                        raise Invalid('packet has missing or unexpected entries')
                    if any((args.directory / name).read_bytes() != data for name, data in expected.items()):
                        raise Invalid('packet does not reconstruct from its exact custody revision')
                    result = {'state': 'reconstructed', 'receipt': original}
                elif args.command == 'checkout':
                    private_write(args.output, json.dumps(case, indent=2, ensure_ascii=False).encode() + b'\n')
                    result = {'state': 'restricted_plaintext_copy', 'receipt': receipt}
                elif args.command == 'check':
                    result = {'ready_errors': ready_errors(case), 'timing': timing(case), 'receipt': receipt}
                elif args.command == 'review':
                    case['review'] = {'reviewer': args.reviewer, 'at': now(), 'checks': sorted(REVIEW_CHECKS)}
                    result = store.append(case, receipt['revision'])
                    result['ready_errors'] = ready_errors(case)
                elif args.command == 'answer':
                    case['answers'].append(strict_load(args.input))
                    case.pop('review', None)
                    result = store.append(case, receipt['revision'])
                elif args.command == 'request':
                    private_write(args.output, request_draft(case, args.request_id, args.follow_up).encode())
                    result = {'state': 'local_draft', 'sent': False}
                elif args.command == 'dispense':
                    files = packet(case, receipt, args.as_of, args.humor, args.ready)
                    # Directory creation is exclusive: never merge a new packet with stale artifacts.
                    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
                    for name, data in files.items():
                        private_write(args.output / name, data)
                    result = {'state': 'local_packet', 'files': sorted(files), 'receipt': receipt, 'published': False}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Invalid, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(f'red-tape: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
