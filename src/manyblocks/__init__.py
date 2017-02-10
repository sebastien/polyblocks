#!/usr/bin/env python2
from __future__ import print_function
import io, os, sys, re, argparse, xml.dom

import texto, texto.parser
import paml
import sugar2.command as sugar
import pythoniccss as pcss
import deparse.core

__doc__ = """
Blocks are files that embed multiple languages together in one interactive
document.
"""

DOM         = xml.dom.getDOMImplementation()
RE_BLOCK    = re.compile("^@(\w+)+\s*(.*)$")
RE_CONTENT  = re.compile("^(\t(.*)|\s*)$")
RE_COMMENT  = re.compile("^#.*$")
DEFAULT_XSL = "block.xsl"

# TODO: Capture stderr from process

# -----------------------------------------------------------------------------
#
# BASIC BLOCK
#
# -----------------------------------------------------------------------------

class Block( object ):

	def __init__( self, name=None, data=None, path=None ):
		super(Block, self).__init__()
		self.name   = name
		self.data   = data
		self.input  = []
		self.output = []
		self.errors = []
		self.path   = path
		self.init()

	def init( self ):
		pass

	def getInput( self ):
		return "\n".join(self.input)

	def getOutput( self ):
		return "\n".join(self.output)

	def getErrors( self ):
		return "\n".join(self.errors)

	def parseLines( self, lines ):
		self.input += lines
		pass

	def toXML( self, doc ):
		pass

	def relpath( self, path ):
		if self.path:
			a = os.path.dirname(os.path.abspath(self.path))
			b = os.path.abspath(path)
			return os.path.relpath(b, a)
		else:
			return path

	def _xml( self, doc, name, *children ):
		node = doc.createElementNS(None, name)
		self._xmlAdd(doc, node, children)
		return node

	def _xmlAdd( self, doc, node, child ):
		if isinstance(child, dict):
			for k,v in child.items():
				node.setAttributeNS(None, k, str(v))
		elif isinstance(child, str) or isinstance(child, unicode):
			node.appendChild(doc.createTextNode(child))
		elif isinstance(child, list) or isinstance(child, tuple):
			[self._xmlAdd(doc, node, _) for _ in child]
		else:
			node.appendChild(child)
		return node

# -----------------------------------------------------------------------------
#
# BLOCKS
#
# -----------------------------------------------------------------------------

# TODO: Implement error management

class MetaBlock( Block ):

	def toXML( self, doc ):
		return self._xml(doc, self.name, self.data)

class TagsBlock( Block ):
	def toXML( self, doc ):
		return self._xml(doc, "tags", [
			self._xml(doc, "tag", _.strip().lower()) for _ in self.data.split() if _.strip()
		]) if self.data else None

class TitleBlock( Block ):
	def toXML( self, doc ):
		return self._xml(doc, "title", self.data.strip()) if self.data else None

class TextoBlock( Block ):

	def parseLines( self, lines ):
		super(TextoBlock, self).parseLines(lines)

	def toXML( self, doc ):
		text   = "\n".join(self.input)
		print (repr(text))
		node   = self._xml(doc, "Texto")
		parser = texto.parser.Parser(self.path, document=doc, root=node)
		parser.parse(text, offsets=False)
		return node


class PamlBlock( Block ):

	def parseLines( self, lines ):
		super(PamlBlock, self).parseLines(lines)
		self.output.append(texto.process("\n".join(lines)))

class Sugar2Block( Block ):

	def init( self ):
		self.imports = []

	def parseLines( self, lines ):
		super(Sugar2Block, self).parseLines(lines)
		text = "@feature sugar\n" + "\n".join(lines) + "\n"
		self.output.append(sugar.process(text))
		deps = deparse.core.Sugar().parseText(text)
		res  = deparse.core.Resolver()
		for t,n in deps.requires:
			# NOTE: This might fail
			self.imports.append([n, res.find(n)[n][0][1]])

	def toXML( self, document ):
		return self._xml(document, "Code",
			{"language":"sugar2"},
			self._xml(document, "imports", [
				self._xml(document, "module", dict(name=_[0], path=self.relpath(_[1]))) for _ in self.imports
			]),
			self._xml(document, "source", document.createCDATASection(self.getInput())),
			self._xml(document, "script", document.createCDATASection(self.getOutput())),
			self._xml(document, "errors", document.createCDATASection(self.getErrors()))
		)

class PCSSBlock( Block ):

	def parseLines( self, lines ):
		self.output.append(pcss.process("\n".join(lines)))

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------

class Parser( object ):

	BLOCKS = dict(
		title  = MetaBlock,
		tags   = TagsBlock,
		author = MetaBlock,
		texto  = TextoBlock,
		paml   = PamlBlock,
		sugar2 = Sugar2Block,
	)

	def __init__( self ):
		self.block  = None
		self.lines  = None
		self.blocks = []
		self.path   = None

	def parseText( self, text, path=None ):
		self.onStart(path)
		for line in text.split("\n"):
			self.onLine(line)
		self.onEnd()

	def parsePath( self, path ):
		self.onStart(path)
		with open(path) as f:
			for l in f.readlines():
				self.onLine(l[:-1])
		self.onEnd()

	def getBlock( self, name, data ):
		block_class = self.BLOCKS[name]
		return block_class(name, data, self.path)

	# =========================================================================
	# PARSING EVENTS
	# =========================================================================

	def onStart( self, path=None ):
		self.path  = path
		self.lines = []
		self.block = None

	def onLine( self, line ):
		m = RE_BLOCK.match(line)
		if m:
			name = m.group(1)
			data = m.group(2)
			block = self.getBlock(name, data)
			self._flushLines()
			self.block = block
			if block not in self.blocks:
				self.blocks.append(block)
			return m
		m = RE_CONTENT.match(line)
		if m:
			self.lines.append(m.group(2) or "")
			return m
		m = RE_COMMENT.match(line)
		if m:
			return m

	def onEnd( self ):
		self._flushLines()
		pass

	# =========================================================================
	# HELPERS
	# =========================================================================

	def _flushLines( self ):
		if self.block:
			self.block.parseLines(self.lines)
			self.lines = []
			self.block = None

# -----------------------------------------------------------------------------
#
# WRITER
#
# -----------------------------------------------------------------------------

class Writer( object ):

	def __init__( self, xsl=DEFAULT_XSL ):
		self.dom = xml.dom.getDOMImplementation()
		self.xsl = xsl

	def write( self, blocks, output, path=None ):
		if isinstance(blocks, Parser): blocks = blocks.blocks
		self.onStart(output, path)
		for block in blocks:
			self.onBlock(block)
		self.onEnd()

	# =========================================================================
	# WRITING EVENTS
	# =========================================================================

	def onStart( self, output, path=None ):
		self.document = self.dom.createDocument(None, None, None)
		self.root     = self.document.createElementNS(None, "Block")
		if self.xsl:
			self.document.appendChild(
				self.document.createProcessingInstruction("xml-stylesheet",
				'type="text/xsl" media="screen" href="{0}"'.format(self.xsl)
			))

		self.document.appendChild(self.root)
		self.output   = output
		self.path     = path

	def onBlock( self, block ):
		node = block.toXML(self.document)
		if node: self.root.appendChild(node)

	def onEnd( self ):
		result = self.document.toprettyxml("\t")
		self.output.write(result)

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

def process( text, path=None, xsl=DEFAULT_XSL ):
	"""Processes the given block `text` (which might have been extracted
	from the given `path`) and returns a string with the result."""
	res = io.BytesIO()
	parser = Parser()
	writer = Writer(xsl=xsl)
	parser.parseText(text, path)
	writer.write(parser, res)
	res.seek(0)
	res = res.read()
	return res

# -----------------------------------------------------------------------------
#
# COMMAND-LINE
#
# -----------------------------------------------------------------------------

def command( args, name=None ):
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "Lists dependencies from PAML and Sugar files"
	)
	# TODO: Rework command lines arguments, we want something that follows
	# common usage patterns.
	oparser.add_argument("files", metavar="FILE", type=str, nargs='+',
			help='The .block files to process')
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	out  = sys.stdout
	parser = Parser()
	writer = Writer()
	for p in args.files:
		parser.parsePath(p)
	writer.write(parser, sys.stdout)

if __name__ == "__main__":
	import sys
	command(sys.argv[1:])

# EOF
