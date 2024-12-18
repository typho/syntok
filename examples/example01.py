#!/usr/bin/env python3

"""
Print slice of string
"""

import os
import sys
import logging
import datetime
import argparse
import unicodedata

LOGGER = logging.getLogger(__name__)


def setup(loglevel, logfmt):
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)


def u_notation(char):
    try:
        name = unicodedata.name(char)
    except ValueError:
        name = '   '
    return 'U+{:04X} {}'.format(ord(char), name)


def main(src, start, end, src_encoding='utf-8'):
    if start > 0 and end > 0 and end < start:
        raise ValueError(f"Unicode codepoint start {start} comes after end {end} - these are meaningless parameters")

    with open(src, encoding=encoding) as fd:
        content = fd.read()[start:end]

    print(f"Unicode scalars {start}—{end}:")
    for i in range(0, len(content), 4):
        print('  ' + ' '.join(u_notation(i) for i in content[i:i + 4]))
    print(f"Unicode scalars {start}—{end}:")
    print('  ' + content)


if __name__ == '__main__':
    loglevels = 'CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING'.split()

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('path', help='source text document to slice')
    parser.add_argument('start', type=int, help='inclusive start of unicode point index')
    parser.add_argument('end', type=int, help='exclusive end of unicode point index')
    parser.add_argument('--encoding', default='utf-8', help='text encoding of source text document')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.path, args.start, args.end, src_encoding=encoding) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)

