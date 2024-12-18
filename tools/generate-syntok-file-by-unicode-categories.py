#!/usr/bin/env python3

"""
Given a source file, assume a character sequence of the same Unicode category is one unit, generate a syntok file.
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
XML_NAMESPACE = 'https://spec.typho.org/syntok/1.0/xml-schema'
CATEGORY_MAP = {
    # via https://www.unicode.org/reports/tr44/#General_Category_Values
    'Lu': 'uppercase-letter',
    'Ll': 'lowercase-letter',
    'Lt': 'titlecase-letter',
    'LC': 'cased-letter',
    'Lm': 'modifier-letter',
    'Lo': 'other-letter',
    'L': 'letter',
    'Mn': 'nonspacing-mark',
    'Mc': 'spacing-mark',
    'Me': 'enclosing-mark',
    'M': 'mark',
    'Nd': 'decimal-number',
    'Nl': 'letter-number',
    'No': 'other-number',
    'N': 'number',
    'Pc': 'connector-punctuation',
    'Pd': 'dash-punctuation',
    'Ps': 'open-punctuation',
    'Pe': 'close-punctuation',
    'Pi': 'initial-punctuation',
    'Pf': 'final-punctuation',
    'Po': 'other-punctuation',
    'P': 'punctuation',
    'Sm': 'math-symbol',
    'Sc': 'currency-symbol',
    'Sk': 'modifier-symbol',
    'So': 'other-symbol',
    'S': 'symbol',
    'Zs': 'space-separator',
    'Zl': 'line-separator',
    'Zp': 'paragraph-separator',
    'Z': 'separator',
    'Cc': 'control',
    'Cf': 'format',
    'Cs': 'surrogate',
    'Co': 'private-use',
    'Cn': 'unassigned',
    'C': 'other'
}


def setup(loglevel, logfmt):
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)


def read_sequences(src, src_encoding):
    with open(src, encoding=src_encoding) as fd:
        cache = ''
        cache_start = 0
        latest_category = ''

        for char in fd.read():
            char_cat = unicodedata.category(char)

            if not latest_category or char_cat == latest_category:
                latest_category = char_cat
                cache += char
            else:
                cache_width = len(cache.encode(src_encoding))
                LOGGER.debug("cache = '{}'  start = {}  category = {}".format(cache, cache_start, latest_category))
                yield {
                    'category': CATEGORY_MAP[latest_category],
                    'start': cache_start,
                    'end': cache_start + cache_width - 1,
                    'content': cache,
                }
                latest_category = char_cat
                cache_start += cache_width
                cache = char

        if latest_category and cache:
            cache_width = len(cache.encode(src_encoding))
            yield {
                'category': CATEGORY_MAP[latest_category],
                'start': cache_start,
                'end': cache_start + cache_width - 1,
                'content': cache,
            }


def main(src, src_encoding):
    doc = xml.sax.saxutils.XMLGenerator(sys.stdout, 'utf-8', short_empty_elements=True)
    doc.startDocument()
    doc.startElement('syntok', {'xmlns': XML_NAMESPACE})
    print()
    LOGGER.info("generating syntok output")

    for item in read_sequences(src, src_encoding):
        print('  ', end='')
        doc.startElement('item', {'category': item['category'], 'start': str(item['start']), 'end': str(item['end'])})
        doc.characters(item['content'])
        doc.endElement('item')
        print()

    doc.endElement('syntok')
    print()
    doc.endDocument()
    LOGGER.info("finished generating syntok output")
 
if __name__ == '__main__':
    loglevels = 'CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING'.split()

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('src', help='source text file to look at')
    parser.add_argument('--src-encoding', default='utf-8', help='text encoding of the original source file')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.src, args.src_encoding) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)
