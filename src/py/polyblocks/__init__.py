#!/usr/bin/env python3
#encoding: UTF-8
from .parser import Cache, Parser, EmbeddedParser
from .writer import XMLWriter, JSONWriter
import io

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

def process( text, path=None ):
	"""Processes the given block `text` (which might have been extracted
	from the given `path`) and returns a string with the result."""
	res = io.StringIO()
	parser = EmbeddedParser()
	writer = XMLWriter()
	parsed = parser.parseText(text, path)
	writer.write(parsed, res)
	res.seek(0)
	res = res.read()
	return res

# EOF - vim: ts=4 sw=4 noet
