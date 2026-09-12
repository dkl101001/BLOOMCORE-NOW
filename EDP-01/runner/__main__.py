# SPDX-License-Identifier: MPL-2.0
import argparse
import json

from analysis.pipeline import analyze, blind, lock_scores

from runner.core import plan, read, run, validate_record, verify_run


def main():
    p = argparse.ArgumentParser(description="EDP-01 experimental instrument")
    s = p.add_subparsers(dest="op", required=True)
    a = s.add_parser("plan")
    a.add_argument("config")
    a = s.add_parser("run")
    a.add_argument("config")
    a.add_argument("--out", required=True)
    a = s.add_parser("verify-run")
    a.add_argument("path")
    a = s.add_parser("verify")
    a.add_argument("record")
    a = s.add_parser("blind")
    a.add_argument("runs", nargs="+")
    a.add_argument("--public", required=True)
    a.add_argument("--private", required=True)
    a = s.add_parser("lock")
    a.add_argument("public")
    a.add_argument("scores")
    a = s.add_parser("analyze")
    a.add_argument("public")
    a.add_argument("private")
    a.add_argument("--out", required=True)
    args = p.parse_args()
    if args.op == "plan":
        result = plan(read(args.config))
    elif args.op == "run":
        result = run(read(args.config), args.out)
    elif args.op == "verify-run":
        result = {"verified_records": len(verify_run(args.path))}
    elif args.op == "verify":
        validate_record(read(args.record))
        result = {"verified": True}
    elif args.op == "blind":
        result = blind(args.runs, args.public, args.private)
    elif args.op == "lock":
        result = lock_scores(args.public, args.scores)
    else:
        result = analyze(args.public, args.private, args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
