#!/usr/bin/env python3

"""
Given the XML output of tree-sitter and the original file,
generate a syntok file.

Why does the XML file not suffice?
  tree-sitter uses Unicode codepoint indices and inserts whitespace.
  Thus the byte offsets cannot be determined.
"""

import io
import os
import sys
import logging
import datetime
import argparse
import xml.sax.saxutils

LOGGER = logging.getLogger(__name__)
XML_NAMESPACE = 'https://spec.typho.org/syntok/1.0/xml-schema'


def setup(loglevel, logfmt):
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)


class TreeSitterXmlReader(xml.sax.handler.ContentHandler):
    """XML SAX reader for .synt specification files"""

    def __init__(self):
        self.level_information = []
        self.parsed_items = []
        self.position_to_byteoffset = {}

    def startElement(self, name, attributes):
        start = self.position_to_byte_offset(int(attributes['srow']), int(attributes['scol']))
        end = self.position_to_byte_offset(int(attributes['erow']), int(attributes['ecol']))

        # NOTE: tree-sitter end positions are exclusive unlike syntok's inclusive end position
        end -= 1

        self.level_information.append({
            'category': name,
            'start': start,
            'end': end
        })

    def endElement(self, name):
        top = self.level_information.pop()

        handled_end = self.parsed_items[-1]['end'] if self.parsed_items else -1
        child_start, child_end = top['start'], top['end']

        if handled_end < child_end:
            # potentially add intermediate element before the popped element
            if handled_end + 1 < child_start:
                self.parsed_items.append({
                    'category': self.level_information[-1]['category'] if self.level_information else 'unit',
                    'start': handled_end + 1,
                    'end': child_start - 1
                })
                handled_end = child_start - 1
            # add element for the popped element
            if handled_end + 1 < child_end:
                self.parsed_items.append({
                    'category': top['category'],
                    'start': max(handled_end + 1, child_start),
                    'end': child_end
                })
                handled_end = child_end


    def characters(self, _data):
        # NOTE: we completely ignore text nodes
        #       because whitespaces were added arbitrarily by tree-sitter
        pass

    def extract_byteoffset_information(self, source_filepath, source_encoding):
        """Read file `source_filepath` and store internal information to power method `position_to_byte_offset`"""
        self.position_to_byteoffset = {}

        # first, we extract the byte offsets of the first characters of lines
        row_id = 0
        self.position_to_byteoffset[(row_id, 0)] = 0

        with open(source_filepath, 'rb') as fd:
            byte_content = fd.read()

        byteoffset = 0
        while True:
            # WARN: we use a simplified model here. We simply consider the byte
            #       after LF starting a new line. This does not respect Unicode UAX #14
            found = byte_content[byteoffset:].find(b'\x0A')
            if found == -1:
                break
            byteoffset += found + 1
            row_id += 1
            self.position_to_byteoffset[(row_id, 0)] = byteoffset

        # second, we add all positions before & after multi-byte characters
        row_id = 0
        col_id = 0
        byteoffset = 0

        with open(source_filepath, 'r', encoding=source_encoding) as fd:
            content = fd.read()

        for char in content:
            if char == b'\n':
                byteoffset += 1
                row_id += 1
                col_id = 0
                continue

            # NOTE: this is a stupid, but pragmatic approach in python.
            #       We have a Unicode string at hand and to determine the number
            #       of bytes, we re-encode the content again (hoping it leads to the
            #       original number of bytes)
            width = len(char.encode(source_encoding))
            if width > 1:
                self.position_to_byteoffset[(row_id, col_id)] = byteoffset
            byteoffset += width
            col_id += 1
            if width > 1:
                self.position_to_byteoffset[(row_id, col_id)] = byteoffset

    def position_to_byte_offset(self, row_id, column_id):
        """Map a given `row_id`,`column_id` tuple to a byte offset"""
        for col_id in range(column_id, -1, -1):
            if (row_id, col_id) in self.position_to_byteoffset:
                # NOTE: the idea is that we record line breaks and multi-byte characters
                #       in position_to_byteoffset. Thus we look for the first entry before
                #       (row_id, column_id) and then just add one for every character
                latest_recorded_byteoffset = self.position_to_byteoffset[(row_id, col_id)]
                byteoffset = latest_recorded_byteoffset + (column_id - col_id)
                return byteoffset

        raise ValueError('Could not map position row={} column={} to any byte offset (internal bug)'.format(row_id, column_id))

    def attach_content(self, source_filepath, source_encoding):
        with open(source_filepath, 'rb') as fd:
            content_bytes = fd.read()
        for item in self.parsed_items:
            start, end = item['start'], item['end']
            content = content_bytes[start:end + 1]
            item['content'] = content.decode(source_encoding)

    def items(self):
        return list(self.parsed_items)

def main(tsxml, src, src_encoding):
    reader = TreeSitterXmlReader()
    reader.extract_byteoffset_information(src, src_encoding)

    with open(tsxml, 'rb') as fd:
        LOGGER.info("extracting data from '{}'".format(tsxml))
        xml.sax.parse(fd, reader)
        LOGGER.info("finished extraction")
    reader.attach_content(src, src_encoding)

    doc = xml.sax.saxutils.XMLGenerator(sys.stdout, 'utf-8', short_empty_elements=True)
    doc.startDocument()
    doc.startElement('syntok', {'xmlns': XML_NAMESPACE})
    print()
    LOGGER.info("generating syntok output")
    for item in reader.items():
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
    parser.add_argument('tsxml', help='XML file with tree-sitter output')
    parser.add_argument('src', help='original source file')
    parser.add_argument('--src-encoding', default='utf-8', help='text encoding of the original source file')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.tsxml, args.src, args.src_encoding) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)
