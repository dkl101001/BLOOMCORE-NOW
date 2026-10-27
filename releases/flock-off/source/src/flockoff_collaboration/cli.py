# SPDX-License-Identifier: Apache-2.0
"""Local relay administration. Never prints room administration capabilities."""
import argparse
import sys
from pathlib import Path
from flockoff_red_tape.ledger import private_write
from .mailbox import MailboxRelay, server
from .protocol import canonical


def port_number(value):
    try: number=int(value)
    except (ValueError,TypeError):raise argparse.ArgumentTypeError('Port must be an integer from 1 to 65535') from None
    if not 1<=number<=65535:raise argparse.ArgumentTypeError('Port must be from 1 to 65535')
    return number


def parser():
    result=argparse.ArgumentParser(description='Self-hosted opaque relay; local bind only. Tor must be configured separately.')
    commands=result.add_subparsers(dest='command',required=True)
    provision=commands.add_parser('provision',help='Create a room and save its private provisioning file')
    provision.add_argument('--database',required=True,type=Path)
    provision.add_argument('--output',required=True,type=Path)
    serve=commands.add_parser('serve',help='Serve on 127.0.0.1 only; no public binding')
    serve.add_argument('--database',required=True,type=Path)
    serve.add_argument('--port',required=True,type=port_number)
    return result


def main(argv=None):
    args=parser().parse_args(argv)
    relay=None;http=None
    try:
        if args.command=='provision':
            if args.output.resolve()==args.database.resolve() or args.output.exists():
                raise ValueError('Provision output must be a new, separate file')
            relay=MailboxRelay(args.database)
            provision=relay.create_space()
            private_write(args.output,canonical(provision)+b'\n')
            print('Private provisioning file created. Deliver it only to the room owner through a trusted channel.')
        else:
            relay=MailboxRelay(args.database)
            http=server(relay,args.port)
            print('Relay listening on 127.0.0.1 only. No Tor service was configured. Press Ctrl+C to stop.')
            http.serve_forever()
        return 0
    except KeyboardInterrupt:
        print('Relay stopped.')
        return 0
    except Exception:
        print('Relay action failed. Check local paths, capacity, permissions and port availability. Existing output is never overwritten; no capabilities are printed.',file=sys.stderr)
        return 1
    finally:
        if http is not None:http.server_close()
        if relay is not None:relay.close()


if __name__=='__main__':
    raise SystemExit(main())
