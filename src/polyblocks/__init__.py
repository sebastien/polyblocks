#!/usr/bin/env python3
from __future__ import print_function
import io, os, sys, re, argparse, xml.dom

import texto, texto.parser
import paml
import sugar2.command as sugar
import pythoniccss as pcss
import hjson, json
import deparse.core

__doc__ = """
Blocks are files that embed multiple languages together in one interactive
document.
"""

DOM         = xml.dom.getDOMImplementation()
RE_BLOCK    = re.compile("^@(\w+)+\s*('[^']+'|\"[^\"]+\"|[^\+]*)\s*(\+[\w\d_-]+\s*)*$")
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

	def __init__( self, name=None, data=None, attributes=None, path=None ):
		super(Block, self).__init__()
		self.name   = name
		self.data   = data
		self.input  = []
		self.output = []
		self.errors = []
		self.path   = path
		self.attributes = attributes
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

	def _xmlAttrs( self, node, attributes=None ):
		if attributes is None:
			attributes = self.attributes
		if isinstance(attributes, list) or isinstance(attributes, tuple):
			for name, value in attributes:
				node.setAttribute(name, "" + (value or ""))
		else:
			for name, value in attributes.items():
				node.setAttribute(name, "" + (value or ""))
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

	description = "Adds meta-information"

	def toXML( self, doc ):
		return self._xml(doc, self.name, self.data)

class TagsBlock( MetaBlock ):

	description = "Block tags as a space-separated list"

	def toXML( self, doc ):
		return self._xml(doc, "tags", [
			self._xml(doc, "tag", _.strip().lower()) for _ in self.data.split() if _.strip()
		]) if self.data else None

class TitleBlock( MetaBlock ):

	description = "Sets the block title"

	def toXML( self, doc ):
		return self._xml(doc, "title", self.data.strip()) if self.data else None

class TextoBlock( Block ):

	description = "A texto markup block"

	def parseLines( self, lines ):
		super(TextoBlock, self).parseLines(lines)

	def toXML( self, doc ):
		text   = "\n".join(self.input)
		node   = self._xml(doc, "Texto")
		parser = texto.parser.Parser(self.path, document=doc, root=node)
		parser.parse(text, offsets=False)
		return self._xmlAttrs(node)


class PamlBlock( Block ):

	description = "A PAML block"

	def parseLines( self, lines ):
		super(PamlBlock, self).parseLines(lines)

	def toXML( self, doc, name="Paml"):
		text     = "\n".join(self.input)
		node     = self._xml(doc, name)
		fragment = doc.createElementNS(None, "fragment")
		source   = doc.createElementNS(None, "source")
		parser = paml.engine.Parser()
		parser._formatter = paml.engine.XMLFormatter(doc, fragment)
		source.appendChild(doc.createTextNode("\n".join(self.input)))
		parser.parseString(text)
		node.appendChild(fragment)
		node.appendChild(source)
		return self._xmlAttrs(node)


class JSXMLBlock( PamlBlock ):

	description = "A PAML/JSXML block"

	def parseLines( self, lines ):
		super(JSXMLBlock, self).parseLines([
			'<?xml version="1.0" encoding="UTF-8"?>',
			'<?xml-stylesheet type="text/xsl" media="screen" href="lib/xsl/jsxml.xsl"?>',
			'<jsx::Component(xmlns::jsx="https://github.com/sebastien/jsxml",xmlns::on="https://github.com/sebastien/jsxml/actions",render="delta")'
		] + ["\t" + _ for _ in lines])

	def toXML( self, doc ):
		xml = super(JSXMLBlock,self).toXML(doc, "JSXML")
		# xml.setAttributeNS("xmlns", "jsx", "https://github.com/sebastien/jsxml")
		# xml.setAttributeNS("xmlns", "on",  "https://github.com/sebastien/jsxml/events")
		# xml.setAttributeNS("xmlns", "x",   "https://github.com/sebastien/jsxml/composition")
		return xml


class Sugar2Block( Block ):

	description = "A Sugar 2 block"

	def init( self ):
		self.imports = []

	def parseLines( self, lines ):
		super(Sugar2Block, self).parseLines(lines)
		text = "@feature sugar\n" + "\n".join(lines) + "\n"
		options = ["-Llib/sjs"]
		# We have a special handling for `.unit.block`: the unit
		# testing is enabled.
		if self.path.endswith(".unit.block"):
			options.append("-Dtests")
		self.output.append(sugar.process(text, 2, options))
		module  = deparse.core.Sugar().parseText(text)
		res     = deparse.core.Resolver()
		# We resolve imported module
		imported = []
		for t,n in module.requires:
			paths = res.find(n)[n]
			if paths:
				imported.append((n,paths[0][1]))
		# and their dependencies
		subimported = []
		for t,n in deparse.core.list([_[1] for _ in imported]):
			paths = res.find(n)[n]
			if paths:
				subimported.append((n,paths[0][1]))
		self.imports = subimported + imported

	def toXML( self, document ):
		return self._xmlAttrs(self._xml(document, "Code",
			{"language":"sugar2"},
			self._xml(document, "imports", [
				self._xml(document, "module", dict(name=_[0], path=self.relpath(_[1]))) for _ in self.imports
			]),
			self._xml(document, "source", document.createCDATASection(self.getInput())),
			self._xml(document, "script", document.createCDATASection(self.getOutput())),
			self._xml(document, "errors", document.createCDATASection(self.getErrors()))
		))

class ComponentBlock( Block ):

	description = "An ff-libs-2 component"

	def parseLines( self, lines ):
		lines       = ["{"] +  ["\t" + _ for _ in lines] + ["}"]
		text        = "\n".join(lines)
		self.output = hjson.loads(text)

	def toXML( self, doc ):
		node  = self._xml(doc, "Component")
		for k,v in self.output.items():
			node.appendChild(self._xmlAttrs(self._xml(doc, "data"), {"name":k, "value":v if type(v) in (str,unicode) else json.dumps(v)}))
		return self._xmlAttrs(node, {"type":self.data})

class PCSSBlock( Block ):

	description = "A PCSS block"

	def parseLines( self, lines ):
		self.output.append(pcss.process("\n".join(lines)))

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------

class Parser( object ):

	BLOCKS = dict(
		title     = MetaBlock,
		subtitle  = MetaBlock,
		focus     = MetaBlock,
		tags      = TagsBlock,
		component = ComponentBlock,
		author    = MetaBlock,
		texto     = TextoBlock,
		paml      = PamlBlock,
		jsxml     = JSXMLBlock,
		sugar2    = Sugar2Block,
	)

	def __init__( self ):
		self.block  = None
		self.lines  = None
		self.blocks = []
		self.path   = None
		self.line   = 0

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

	def getBlock( self, name, data, attrs ):
		block_class = self.BLOCKS.get(name)
		if not block_class:
			raise Exception("No block defined for tag: `@{0}` at line {1} in {2}".format(name, self.line, self.path))
		else:
			return block_class(name, data, attrs, self.path)

	# =========================================================================
	# PARSING EVENTS
	# =========================================================================

	def onStart( self, path=None ):
		self.line  = 0
		self.path  = path
		self.lines = []
		self.block = None

	def onLine( self, line ):
		# NOTE: We need to make sure the input is unicode
		self.line += 1
		line = line.decode("utf8")
		m = RE_BLOCK.match(line)
		if m:
			name   = m.group(1)
			data   = (m.group(2) or "").strip()
			attrs  = m.group(3) or ""
			if data and data[0] == data[-1] and data[0] in '"\'':
				data = data[1:-1]
			attrs = (_.strip().split("=",1) for _ in attrs.split() if _.strip())
			attrs = [(_[0][1:], _[1] if len(_) > 1 else "true") for _ in attrs]
			block = self.getBlock(name, data, attrs)
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
		self.meta     = self.document.createElementNS(None, "Meta") ; self.root.appendChild(self.meta)
		self.content  = self.root
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
		if node:
			self.getXMLRoot(block).appendChild(node)

	def getXMLRoot( self, block ):
		if isinstance(block, MetaBlock):
			return self.meta
		else:
			return self.content

	def onEnd( self ):
		result = self.document.toprettyxml("\t", encoding="utf8")
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

def command( args, name="polyblocks" ):
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "Lists dependencies from PAML and Sugar files"
	)
	# TODO: Rework command lines arguments, we want something that follows
	# common usage patterns.
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*',
			help='The .block files to process')
	oparser.add_argument("--list", action="store_true",
			help='List the available block types')
	# We create the parse and register the options
	args = oparser.parse_args(args=args)
	out  = sys.stdout
	if args.list:
		for key in sorted(Parser.BLOCKS):
			out.write("@{0:10s} {1}\n".format(key, Parser.BLOCKS[key].description))
	elif args.files:
		parser = Parser()
		writer = Writer()
		for p in args.files:
			parser.parsePath(p)
		writer.write(parser, sys.stdout)

if __name__ == "__main__":
	import sys
	command(sys.argv[1:])

# EOF
