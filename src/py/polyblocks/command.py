#!/usr/bin/env python3
#encoding: UTF-8
import os, sys, argparse
from .parser import Cache, Parser, EmbeddedParser
from .writer import XMLWriter, JSONWriter

# FIXME: This should probably be a canonical URL
DEFAULT_XSL = "lib/xsl/polyblocks.xsl"

# -----------------------------------------------------------------------------
#
# COMMAND-LINE
#
# -----------------------------------------------------------------------------

# @symbol polyblocks.command
# @embed|shell polyblocks --help
def run( args, name="polyblocks" ):
	"""Runs the polyblocks command, parsing the given arguments as command-line
	arguments."""
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "TODO"
	)
	# TODO: Rework command lines arguments, we want something that follows
	# common usage patterns.
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*',
		help='The .block files to process')
	oparser.add_argument("--list", action="store_true",
		help='List the available block types')
	oparser.add_argument("-O", "--output-format", choices=("xml","json"), default="xml",
		help='Defines the output format')
	oparser.add_argument("-p", "--pretty", action="store_true",
		help='Pretty prints the XML output')
	oparser.add_argument("-s", "--stylesheet", action="store", default=DEFAULT_XSL,
		help='Specifies the stylesheet URL, can be empty')
	oparser.add_argument("-cc", "--clean-cache", action="store_true",
		help='Cleans the cache')
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	out  = sys.stdout
	if args.clean_cache:
		Cache.Ensure().clean(full=True)
	# if args.list:
	# 	for key in sorted(Parser.BLOCKS):
	# 		out.write("@{0:10s} {1}\n".format(key, Parser.BLOCKS[key].description))
	elif args.files:
		parser = EmbeddedParser()
		writer = None
		if args.output_format == "xml":
			writer = XMLWriter(pretty=args.pretty)
		elif args.output_format == "json":
			writer = JSONWriter(pretty=args.pretty)
		for p in args.files:
			writer.write(parser.parsePath(p), sys.stdout)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	import sys
	run(sys.argv[1:])

# EOF - vim: ts=4 sw=4 noet
