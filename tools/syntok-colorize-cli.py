#!/usr/bin/env python3

"""
Generate a CLI representation of the content of some `.syn` file
using ANSI escape sequences (ECMA 48) for VT100 terminals for coloring.
"""

import sys
import hashlib
import logging
import datetime
import argparse
import xml.sax
import xml.sax.handler

LOGGER = logging.getLogger(__name__)
DEFAULT_COLORS = '0;34;49 0;31;49 0;35;49 0;33;49 0;36;49 0;32;49 0;37;49'.split()
COLOR_ASSIGNMENT = {}


def integrate_colors_globally(color_specs):
    """Read provided `color_specs` CLI arguments and
    adjust global variable `COLOR_ASSIGNMENT` accordingly
    """
    global COLOR_ASSIGNMENT

    for color_spec in color_specs:
        if color_spec.count(':') != 1:
            raise ValueError("Color specification must separate category from ANSI escape sequence with a colon; not a single colon found but '{}'".format(color_spec))
        name, ansi_seq = color_spec.split(':')
        COLOR_ASSIGNMENT[name.strip()] = ansi_seq.strip()

    if COLOR_ASSIGNMENT:
        LOGGER.debug("color assignment defined by CLI arguments = {}".format(COLOR_ASSIGNMENT))


class SynRepresenter(xml.sax.handler.ContentHandler):
    """XML SAX reader and CLI printer for `.syn` file content

    (1) handles the `.synt` file XML content as SAX parser
    (2) generate the representation for contained tokens
    (3) print representation to CLI with ANSI escape sequences
    """
    def __init__(self):
        super().__init__()
        self.in_item = False

    @staticmethod
    def category_to_color_id(category_name, count_colors):
        """Given a `category_name` defined in the `.syn` file and the number of colors `N`,
        return an index for a color with 1 ≤ index < N
        """
        h = hashlib.new('sha256')
        h.update(category_name.encode('utf-8'))
        dig = h.digest()
        return sum(2 * d + 7 * i for i, d in enumerate(dig)) % count_colors

    @staticmethod
    def start_color(category_name):
        """Print ANSI escape sequence to colorize following token"""
        global COLOR_ASSIGNMENT
        color = None

        if category_name in COLOR_ASSIGNMENT:
            color = COLOR_ASSIGNMENT[category_name]
        else:
            color_id = SynRepresenter.category_to_color_id(category_name, len(DEFAULT_COLORS))
            color = DEFAULT_COLORS[color_id]
            COLOR_ASSIGNMENT[category_name] = color

        print('\x1B[{}m'.format(color), end='')

    @staticmethod
    def end_color():
        """Print ANSI escape sequence to stop any colorization"""
        print('\x1B[0;39;49m', end='')

    def startElement(self, name, attributes):
        if name == 'item':
            self.in_item = True

        if self.in_item:
            self.start_color(attributes['category'])

    def endElement(self, _name):
        if self.in_item:
            self.end_color()
            self.in_item = False

    def characters(self, data):
        if not self.in_item:
            return
        print(data, end='')


def setup(loglevel, logfmt):
    """Setup internal tooling"""
    logging.basicConfig(level=loglevel, format=logfmt)
    LOGGER.setLevel(loglevel)


def main(filepath, color_specifiers):
    """Main routine"""
    if color_specifiers:
        integrate_colors_globally(color_specifiers)

    with open(filepath) as fd:
        xml.sax.parse(fd, SynRepresenter())

    LOGGER.debug('color assignment used = {}'.format(COLOR_ASSIGNMENT))


if __name__ == '__main__':
    loglevels = 'CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING'.split()

    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('src', help='the .syn file specifying tokens and content to represent in a colorful way')
    parser.add_argument('-c', '--color', action='append', help='ANSI escape sequence between "\\x1B[" and "m" colon-separated from category to specify color for one category, e.g. "identifier:0;31;49"')
    parser.add_argument('--log-level', dest='loglevel', default='WARN', choices=loglevels, help='loglevel for the logging module')
    parser.add_argument('--log-format', dest='logformat', default='%(asctime)s,%(levelname)s: %(message)s', help='log message for the logging module')

    args = parser.parse_args()
    setup(loglevel=getattr(logging, args.loglevel), logfmt=args.logformat)
    LOGGER.debug("start at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    exitcode = main(args.src, args.color) or 0
    LOGGER.debug("end at {} UTC".format(datetime.datetime.now(datetime.UTC).isoformat()))
    sys.exit(exitcode)
