# SPDX-License-Identifier: MPL-2.0
import argparse
import json

from analysis.pipeline import analyze, blind, lock

from runner.core import plan, read, run, verify_run


def main():
    p = argparse.ArgumentParser(description="EDP-02 experimental checkpoint protocol")
    s = p.add_subparsers(dest="command", required=True)
    a = s.add_parser("plan")
    a.add_argument("config")
    a = s.add_parser("run")
    a.add_argument("config")
    a.add_argument("--out", required=True)
    a = s.add_parser("verify")
    a.add_argument("run")
    a = s.add_parser("blind")
    a.add_argument("run")
    a.add_argument("--public", required=True)
    a.add_argument("--private", required=True)
    a = s.add_parser("lock")
    a.add_argument("public")
    a.add_argument("ratings")
    a = s.add_parser("analyze")
    a.add_argument("public")
    a.add_argument("private")
    a.add_argument("--out", required=True)
    a = p.parse_args()
    if a.command == "plan":
        r = plan(read(a.config))
    elif a.command == "run":
        r = run(read(a.config), a.out)
    elif a.command == "verify":
        r = {"verified_records": len(verify_run(a.run))}
    elif a.command == "blind":
        r = blind(a.run, a.public, a.private)
    elif a.command == "lock":
        r = lock(a.public, a.ratings)
    else:
        r = analyze(a.public, a.private, a.out)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
