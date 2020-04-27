#!/usr/bin/env python3
import argparse
import io
import os
import re
import sys
from . import GazelleAPI, GazelleAPIError


EXIT_CODES = {
    'hash': 3,
    'music': 4,
    'unauthorized': 5,
    'request': 6,
    'request-json': 7,
    'api-key': 8,
    'tracker': 9,
}

parser = argparse.ArgumentParser(
    description='Fetches torrent origin information from Gazelle-based music trackers',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog='--tracker is optional if the ORIGIN_TRACKER environment variable is set.\n\n'
           'If provided, --tracker must be set to one of the following: red\n'
)
parser.add_argument('id', help='torrent identifier, which can be either its info hash, torrent ID, or permalink')
parser.add_argument('--out', '-o', help='path to write origin data (default: print to stdout)', metavar='file')
parser.add_argument('--tracker', '-t', nargs=1, metavar='tracker', help='tracker to use')


def main():
    args = parser.parse_args()

    api_key = os.environ.get('RED_API_KEY')
    if not api_key:
        print('RED_API_KEY environment variable not set.', file=sys.stderr)
        sys.exit(EXIT_CODES['api-key'])

    tracker = args.tracker[0] if args.tracker else os.environ.get('ORIGIN_TRACKER')
    if not tracker:
        print('Tracker must be provided using either --tracker or setting the ORIGIN_TRACKER environment variable.',
                file=sys.stderr)
        sys.exit(EXIT_CODES['tracker'])
    if tracker.lower() != 'red':
        print('Invalid tracker: {0}'.format(tracker), file=sys.stderr)
        sys.exit(EXIT_CODES['tracker'])

    try:
        api = GazelleAPI(api_key)

        if re.match(r'^[\da-fA-F]{40}$', args.id):
            info = api.get_torrent_info(hash=args.id)
        elif re.match(r'^\d+$', args.id):
            info = api.get_torrent_info(id=args.id)
        else:
            match = re.match(r'.*torrentid=(\d+)', args.id)
            if not match:
                print('Invalid torrent ID or hash', file=sys.stderr)
                sys.exit(EXIT_CODES['hash'])
            info = api.get_torrent_info(id=match[1])
    except GazelleAPIError as e:
        print(e, file=sys.stderr)
        sys.exit(EXIT_CODES[e.code])

    if args.out:
        with io.open(args.out, 'w', encoding='utf-8') as f:
            f.write(info)
    else:
        print(info, end="")


if __name__ == '__main__':
    main()
