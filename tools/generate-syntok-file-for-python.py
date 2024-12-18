#!/usr/bin/env python3

"""
Take a source text file, identify consecutive strings of latin characters as one unit and print byte offsets of all units.
In simpler terms, this is a heuristic program to generate a .synt file for a python source file.
"""

import re
import os
import sys
import logging
import datetime
import argparse
import unicodedata
import xml.sax.saxutils

LOGGER = logging.getLogger(__name__)

def setup(loglevel, logfmt):
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)

def item(category, content, start, end):
    template = '  <item category="{category}"{w1} start="{start}"{w2} end="{end}"{w3}>{content}</item>'
    #template = '\033[1;34;49m«\0330;39;49m{}\033[1;34;49m»\0330;39;49m @ {}–{}'
    w1 = ' ' * (12 - len(category))
    w2 = ' ' * (4 - len(str(start)))
    w3 = ' ' * (4 - len(str(end)))
    content = xml.sax.saxutils.escape(content)
    print(template.format(category=category, content=content, start=start, end=end, w1=w1, w2=w2, w3=w3))

def cat(cpoint):
    match cpoint[0]:
        case ' ' | '\t':
            return 'whitespace'
        case '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '0':
            return ''
        case '\n':
            return 'newline'
        case ':' | '(' | ')' | '[' | ']' | '{' | '}' | '.' | '=' | ',':
            return 'operator'
        case '"' | "'":
            return 'string'
        case '#':
            return 'comment'
    match cpoint:
        case 'import' | 'or' | 'and':
            return 'keyword'
    return 'identifier'
    #raise ValueError("Unclassified '{}'".format(cpoint))

def main(src):
    with open(src) as fd:
        content = fd.read()
        current = 0
        print('<?xml version="1.0" encoding="utf-8"?>')
        print('<syntok xmlns="https://spec.typho.org/syntok/1.0/xml-schema">')
        for m in re.finditer('(#[^\n]*|\\w+| +|\n+|"+[^"]+"+|\'+[^\']+\'+)', content):
            while current != m.start():
                category = cat(content[current])
                item(category, content[current], current, current)
                current += 1
            category = cat(m.group(0))
            item(category, m.group(0), m.start(), m.end() - 1)
            current = m.end()
        while current < len(content):
            category = cat(content[current])
            item(category, content[current], current, current)
            current += 1
        print('</syntok>')
 
if __name__ == '__main__':
    loglevels = 'CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING'.split()

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('src', help='source text file to look at')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.src) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)
