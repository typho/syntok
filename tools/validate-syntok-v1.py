#!/usr/bin/env python3

"""
The XSD file cannot validate the partition property of byte offsets.
This python program verifies this additional property for a given .synt file.
In fact, it verifies all properties of the syntok specification

The file passes the testsuite if 'PASS ' is printed on stdout or its exitcode is zero.
"""

import re
import sys
import logging
import datetime
import argparse

import xml.sax.handler
import xml.sax

LOGGER = logging.getLogger(__name__)
NAMESPACE = 'https://spec.typho.org/syntok/1.0/xml-schema'
CATEGORY_REGEX = '[_a-zA-Z][_a-zA-Z0-9-]*'

class XMLSAXReader(xml.sax.handler.ContentHandler):
    """XML SAX reader for .synt specification files"""

    def __init__(self):
        self.element_path = []
        self.item_content = None
        self.item_content_encoding = None
        self.current_byte_offset = None

    def startElement(self, name, attributes):
        if not self.element_path and name != 'syntok':
            raise ValueError("Unexpected root element '{}'; expected 'syntok' element".format(name))
        elif self.element_path == ['syntok'] and name != 'item':
            raise ValueError("Unexpected element '{}' in /syntok; expected 'item' element".format(name))
        elif len(self.element_path) > 2:
            raise ValueError("Only root element /syntok and subelement /syntok/item are allowed; got '{}' in /{}".format(name, '/'.join(self.element_path)))

        if name == 'syntok':
            self.verifySyntokElement(attributes)
        elif name == 'item':
            self.verifyItemElement(attributes)
            self.item_content_encoding = attributes.get('encoding', 'string')
            self.current_byte_offset = int(attributes['end'])

        self.element_path.append(name)

    def endElement(self, name):
        # verify hex content
        if self.element_path == ['syntok', 'item']:
            if self.item_content_encoding == 'hex':
                if not re.fullmatch('([0-9A-F][0-9A-F])*', self.item_content):
                    raise ValueError("Item content must be uppercase hexadecimal content of bytes, but is '{}'".format(self.item_content))
            self.item_content = None
            self.item_content_encoding = None
        self.element_path.pop()

    def characters(self, data):
        if self.element_path == ['syntok', 'item']:
            # collect <item> content
            if not self.item_content:
                self.item_content = ''
            self.item_content += data
        else:
            if data.strip() != '':
                raise ValueError("Unexpected string content: '{}'".format(data))

    def verifySyntokElement(self, attributes):
        pass

    def verifyItemElement(self, attributes):
        def as_int(attr):
            # 'start' attribute
            val = attributes.get(attr)
            try:
                val = int(val)
                if val < 0:
                    raise ValueError("Attribute '{}' must be non-negative, but found '{}'".format(attr, val))
            except ValueError:
                raise ValueError("Attribute '{}' must be non-negative integer, but found '{}'".format(attr, val))
            return val

        start = as_int('start')
        end = as_int('end')

        if end < start:
            raise ValueError("Attribute 'end' of an element must be greater or equal to its 'start' attribute, but {} < {} is given".format(end, start))

        if self.current_byte_offset and self.current_byte_offset + 1 != start:
            raise ValueError("start–end range must provide a partitioned document, but a gap has been found between end {} and start {}".format(self.current_byte_offset, start))

        category = attributes.get('category')
        if not category:
            raise ValueError("Attribute 'category' is missing for item at start {} and end {}", start, end)
        if not re.fullmatch(CATEGORY_REGEX, category):
            raise ValueError("Category '{}' does not match the required regular expression".format(category))


def setup(loglevel, logfmt):
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)


def main(src):
    with open(src) as fd:
        xml.sax.parse(fd, XMLSAXReader())

    # if not ValueError was raised during parsing, the specification is fulfilled
    print("PASS  File '{}' is valid - it satisfies the specification".format(src))


if __name__ == '__main__':
    loglevels = 'CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING'.split()

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('src', help='syntok source file to validate')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.src) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)
