#!/usr/bin/env python3
from __future__ import print_function
import io, os, sys, re, argparse, xml.dom, time, pickle, hashlib, stat, json

__doc__ = """
Blocks are files that embed multiple languages together in one interactive
document.
"""

# --- OPTIONAL IMPORTS --------------------------------------------------------

try:
	import texto, texto.parser
except ImportError as e:
	texto = None

try:
	import paml
except ImportError as e:
	paml = None

try:
	import sugar2.command as sugar
except ImportError as e:
	sugar = None

try:
	import pythoniccss as pcss
except ImportError as e:
	pcss = None

try:
	import deparse.core
except ImportError as e:
	deparse = None

DOM         = xml.dom.getDOMImplementation()
RE_BLOCK    = re.compile("^@(\w+)+\s*('[^']+'|\"[^\"]+\"|[^\+]*)\s*(\+[\w\d_-]+\s*)*$")
RE_CONTENT  = re.compile("^(\t(.*)|\s*)$")
RE_COMMENT  = re.compile("^#.*$")
DEFAULT_XSL = "block.xsl"

# TODO: Capture stderr from process

def parseAttributes( text ):
	"""A simple parser that extract (key,value) from a string like
	`KEY=VALUE,KEY="VALUE\"VALUE",KEY='VALUE\'VALUE'`"""
	offset = 0
	result = []
	while offset < len(text):
		equal  = text.find("=", offset)
		assert equal >= 0, "Include subsitution without value: {0}".format(text)
		name   = text[offset:equal]
		offset = equal + 1
		if offset == len(text):
			value = ""
		elif text[offset] in  '\'"':
			# We test for quotes and escape it
			quote = text[offset]
			end_quote = text.find(quote, offset + 1)
			while end_quote >= 0 and text[end_quote - 1] == "\\":
				end_quote = text.find(quote, end_quote + 1)
			value  = text[offset+1:end_quote].replace("\\" + quote, quote)
			offset = end_quote + 1
			if offset < len(text) and text[offset] == ",": offset += 1
		else:
			# Or we look for a comma
			comma  = text.find(",", offset)
			if comma < 0:
				value  = text[offset:]
				offset = len(text)
			else:
				value  = text[offset:comma]
				offset = comma + 1
		result.append((name.strip(), value))
	return result

# -----------------------------------------------------------------------------
#
# BASIC BLOCK
#
# -----------------------------------------------------------------------------

class Block( object ):

	KEY = ["name", "data", "attributes", "path"]
	IDS = 0

	def __init__( self, name=None, data=None, attributes=None, path=None ):
		super(Block, self).__init__()
		self.id     = self.__class__.IDS ; self.__class__.IDS += 1
		self.name   = name
		self.data   = data
		self.input  = []
		self.output = []
		self.errors = []
		self.path   = path
		self.attributes = attributes
		self.init()

	def key( self ):
		return json.dumps([getattr(self, _) for _ in self.KEY])

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
		elif child:
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

class HeadingBlock( Block ):

	description = "Creates a new section/subsection"

	def toXML( self, doc ):
		return self._xml(doc, "Heading", dict(depth=self.name[1:]), self.data.strip()) if self.data else None

class ImportBlock( MetaBlock ):

	description = "Imports files/modules"

	def toXML( self, doc ):
		return self._xml(doc, "import", [
			self._xml(doc, "module", dict(
				type=_.strip().rsplit(".",1)[-1],
				basename=os.path.basename(_),
				name=os.path.basename(_).rsplit(".",1)[0]
			), _.strip()) for _ in self.data.split() if _.strip()
		]) if self.data else None


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

	def init( self ):
		self.title = None
		self.attrs = {}

	def parseLines( self, lines ):
		super(PamlBlock, self).parseLines(lines)
		title_attrs = self.data.split("+",1)
		self.title = title_attrs[0].strip()
		self.attrs = {}
		if len(title_attrs) == 2:
			self.attrs.merge(parseAttributes(title_attrs[1]))

	def toXML( self, doc, name="Paml"):
		text     = "\n".join(self.input)
		node     = self._xml(doc, name)
		fragment = doc.createElementNS(None, "fragment")
		source   = doc.createElementNS(None, "source")
		parser = paml.engine.Parser()
		if self.title:
			node.setAttribute("title", self.title)
		for k,v in self.attrs.items():
			node.setAttribute(k, v)
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

class PAMLXMLBlock( PamlBlock ):

	description = "A PAML/XML block"

	def parseLines( self, lines ):
		super(PAMLXMLBlock, self).parseLines([
			'<?xml version="1.0" encoding="UTF-8"?>',
		] + ["\t" + _ for _ in lines])

	def toXML( self, doc ):
		xml = super(PAMLXMLBlock,self).toXML(doc, "XML")
		return xml


class Sugar2Block( Block ):

	description = "A Sugar 2 block"

	def init( self ):
		self.imports = []

	def parseLines( self, lines ):
		super(Sugar2Block, self).parseLines(lines)
		sg_backend = os.environ["SUGAR_BACKEND"] if "SUGAR_BACKEND" in os.environ else "es"
		sg_modules = os.environ["SUGAR_MODULES"] if "SUGAR_MODULES" in os.environ else "umd"
		text = "@feature sugar\n" + "\n".join(lines) + "\n"
		options = ["-Llib/sjs", "-l" + sg_backend, "-D" + sg_modules]
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
		super(PCSSBlock, self).parseLines(lines)
		res = pcss.process("\n".join(lines) + "\n")
		self.output.append(res)

	def toXML( self, document ):
		errors = self.getErrors ()
		return self._xmlAttrs(self._xml(document, "PCSS",
			{"language":"pcss"},
			self._xml(document, "source", document.createCDATASection(self.getInput())),
			self._xml(document, "script", document.createCDATASection(self.getOutput())),
			self._xml(document, "errors", document.createCDATASection(errors)) if errors else None
		))

class ShaderBlock( Block ):

	description = "A WebGL shader block"

	def parseLines( self, lines ):
		text        = "\n".join(lines)
		self.output = text

	def toXML( self, doc ):
		node  = self._xml(doc, "Shader")
		node.appendChild(self._xml(doc, "source", doc.createCDATASection(self.output)))
		return self._xmlAttrs(node, {"name":self.data or "shader-{0}".format(self.id)})

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------

class Parser( object ):

	BLOCKS = {
		"title"     : MetaBlock,
		"subtitle"  : MetaBlock,
		"h1"        : HeadingBlock,
		"h2"        : HeadingBlock,
		"h3"        : HeadingBlock,
		"h4"        : HeadingBlock,
		"h5"        : HeadingBlock,
		"h6"        : HeadingBlock,
		"focus"     : MetaBlock,
		"tags"      : TagsBlock,
		"component" : ComponentBlock,
		"shader"    : ShaderBlock,
		"author"    : MetaBlock,
		"texto"     : TextoBlock,
		"paml"      : PamlBlock,
		"pcss"      : PCSSBlock,
		"jsxml"     : JSXMLBlock,
		"pamxml"    : PAMLXMLBlock,
		"sugar2"    : Sugar2Block,
		"import"    : ImportBlock,
	}

	def __init__( self ):
		self.block  = None
		self.lines  = None
		self.blocks = []
		self.path   = None
		self.line   = 0
		self.cache  = Cache.Ensure()

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
			text = u"\n".join(self.lines)
			if self.cache.has(text, self.block):
				i = self.blocks.index(self.block)
				b = self.cache.get(text, self.block)
				self.blocks[i] = b
			else:
				self.block.parseLines(self.lines)
				if text:
					self.cache.set(text, self.block, self.block)
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

class Cache:
	"""A simple self-cleaning cache."""

	CACHE = None

	@classmethod
	def Ensure(cls):
		if not cls.CACHE:
			return Cache(os.path.expanduser("~/.cache/polyblocks"))

	def __init__( self, path ):
		self.root = path
		assert path
		if not os.path.exists(path):
			os.makedirs(path)

	def key( self, text, block ):
		"""Gets the key for the given text as processed by the given block."""
		text = block.__class__.__name__ + block.key() + (text or "")
		return self.hash(text)

	def hash( self, text ):
		return hashlib.sha256(text.encode("utf8")).hexdigest()

	def has( self, text, block ):
		if not text: return False
		key = self.key(text, block)
		return key and os.path.exists(self._path(key))

	def get( self, text, block ):
		if not text: return None
		key = self.key(text, block)
		if self.has(text, block):
			with open(self._path(key), "r") as f:
				return pickle.load(f)
		return None

	def set( self, text, block, value ):
		if not text: return text
		self.clean()
		key = self.key(text, block)
		with open(self._path(key), "w") as f:
			pickle.dump(value, f)
		return value

	def clean( self ):
		now = time.time()
		for _ in list(os.listdir(self.root)):
			p = os.path.join(self.root, _)
			s = os.stat(p)[stat.ST_MTIME]
			if now - s > 60 * 60 * 24:
				os.unlink(p)

	def _path( self, key ):
		assert key
		return os.path.join(self.root, key + ".cache")

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
