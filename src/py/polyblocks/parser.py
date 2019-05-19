#!/usr/bin/env python3
#encoding: UTF-8
from .model  import Block
from .inputs import BlockHeader,BlockInput,DateInput,ListInput,TextInput,CodeInput,HeadingInput,MetaInput
from .inputs.paml import PamlInput
from .util   import Cache
from typing  import Optional,List,Iterable,Dict,NamedTuple,Any,Type
import re,collections

__doc__ = """
Defines the Polyblocks parser classes.
"""

# -----------------------------------------------------------------------------
#
# MAPPING
#
# -----------------------------------------------------------------------------

#@symbol polyblocks.parser.Mapping
class Mapping:

	TAGS = {
		"title"    : HeadingInput,
		"subtitle" : HeadingInput,
		"date"     : DateInput,
		"created"  : DateInput,
		"updated"  : DateInput,
		"tags"     : ListInput,

		"embed"    : CodeInput,

		"h1"       : HeadingInput,
		"h2"       : HeadingInput,
		"h3"       : HeadingInput,
		"h4"       : HeadingInput,
		"h5"       : HeadingInput,
		"h6"       : HeadingInput,

		"symbol"   : MetaInput,
		"anchor"   : MetaInput,
	}

	TYPES = {
		"date"      : DateInput,
		"list"      : ListInput,
		"text"      : TextInput,
		"code"      : CodeInput,
		# --
		"texto"     : CodeInput,
		# "paml"      : PamlInput,
		# "pcss"      : PCSSInput,
		# "texto"     : TextoInput,
		# "sugar"     : SugarInput,
	}

	def __init__( self ):
		pass

	def getInputForType( self, name:str ) -> Optional[Type[BlockInput]]:
		return self.TYPES.get(name)

	def getInputForTag( self, name:str ) -> Optional[Type[BlockInput]]:
		return self.TAGS.get(name, self.TYPES.get(name))

	def getInputForHeader( self, header:'BlockHeader' ) -> Optional[Type[BlockInput]]:
		return self.getInputForTag(header.name) or self.getInputForType(header.type)

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------


#@symbol polyblocks.parser.Parser
class Parser:
	"""Parses the polyblock text format, using the `Mapping` to define
	which the block names and input formats are available."""

	# A block header is like `@NAME:TYPE|P0,P1 CONTENT… 
	RE_HEADER   = re.compile("^@(\w+)(:\w+)?(\|[\w\-_]+(,[\w\-_]+)?)?(\s+(.*))?\s*$")
	RE_CONTENT  = re.compile("^(\t(.*)|\s*)$")
	RE_COMMENT  = re.compile("^#.*$")

	def __init__( self ):
		# We keep a list of block inputs as well as a current
		# block input. Lines will be fed to the block inputs
		# and then the blocks will be created from the contents.
		self.blockInput:Optional[BlockInput] = None
		self.blockInputs:List[BlockInput] = []
		# That's the path currently being parsed
		self.path:Optional[str]    = None
		# That's the current parsed line
		self.line                  = 0
		# The cache prevents from having to process the same input
		# twice.
		self.cache                 = Cache.Ensure()
		# The mapping defines the available block names and types
		self.mapping               = Mapping()

		# TODO: Is this used at all?
		self.lines:List[str]       = []
		self.rawLines:List[str]    = None

	def parseText( self, text:str, path:Optional[str]=None ) -> List[Block]:
		"""Parses the given `text`, loaded from the given `path` (optional).
		The text is going to be split into lines and fed to  `parseLines`."""
		return self.parseLines(text.split("\n"), path)

	def parsePath( self, path:str ) -> List[Block]:
		"""Parses the text at the given `path`."""
		with open(path, "rt") as f:
			return self.parseLines(f.readlines(), path)

	def parseLines( self, lines:Iterable[str], path:Optional[str] ) -> List[Block]:
		"""Parses the given `lines`, coming from a file at the given
		`path`."""
		self.onStart(path)
		for line in lines:
			self.onLine(line)
		return self.onEnd()

	# =========================================================================
	# HEADER PARSING
	# =========================================================================

	def parseHeaderLine( self, line:str ) -> Optional[BlockHeader]:
		"""Parses a block header line (ie `@type:name|processors CONTENT`)
		and returns a Header structure if matched."""
		match      = self.RE_HEADER.match(line)
		# NOTE: This should probably raise a parsing error
		if not match: return None
		type       = match.group(2) or match.group(1)
		name       = match.group(1) if not match.group(2) else None
		processors = [_.strip() for _ in match.group(2)[1:].split(",")] if match.group(2) else []
		rest       = match.group(6) or ""
		# NOTE: The line is always stripped, but that might now be what
		# we always want to do.
		line       = rest
		attributes:Dict[str,Any] = {}
		i = line.find("{")
		j = line.rfind("{")
		if i >= 0 and i < j:
			line = rest[:i].strip()
			attributes = self.parseHeaderAttributes(rest[i+1:j-1])
		return BlockHeader(name,type,processors,attributes,line)

	def parseHeaderAttributes( self, line:str ) -> Dict[str,Any]:
		"""A simple parser that extract (key,value) from a string like
		`KEY=VALUE,KEY="VALUE\"VALUE",KEY='VALUE\'VALUE'`"""
		offset = 0
		result:Dict[str,Any] = dict()
		while offset < len(line):
			equal = line.find("=", offset)
			if equal == -1:
				comma = line.find(",",offset)
				if comma == -1:
					sep = len(line)
				else:
					sep = comma
			else:
				sep = equal
			name   = line[offset:sep]
			offset = sep + 1
			if offset >= len(line):
				value = ""
			elif line[offset] in  '\'"':
				# We test for quotes and escape it
				quote = line[offset]
				end_quote = line.find(quote, offset + 1)
				while end_quote >= 0 and line[end_quote - 1] == "\\":
					end_quote = line.find(quote, end_quote + 1)
				value  = line[offset+1:end_quote].replace("\\" + quote, quote)
				offset = end_quote + 1
				if offset < len(line) and line[offset] == ",": offset += 1
			else:
				# Or we look for a comma
				comma  = line.find(",", offset)
				if comma < 0:
					value  = line[offset:]
					offset = len(line)
				else:
					value  = line[offset:comma]
					offset = comma + 1
			result[name.strip()] = value or True
		return result

	# =========================================================================
	# PARSING EVENTS
	# =========================================================================

	def onStart( self, path:Optional[str]=None ):
		"""Called when the parsing starts, initializes the parser state."""
		self.line      = 0
		self.path      = path
		self.blockInput = None
		self.blockInputs = []

	def onLine( self, line:str ) -> bool:
		"""Called when a line is fed into the parser."""
		# --- BLOCK LINE
		# If the line starts with `@` then it's a block declaration
		if line.startswith("@"):
			# We parse the header line, 
			header = self.parseHeaderLine(line)
			if not header:
				# TODO: We have a potentially malformed line, we should
				# surface it to the user.
				pass
			else:
				# We create a block from the header
				block_input  = self._createBlockInputFromHeader(header)
				# We notify that a new block is starting, which by default
				# flushes all parsed lines and assigns them to the current block
				# The new block becomes the current block
				self.blockInput = block_input
				self.blockInputs.append(block_input)
				self.onBlockStart(header)
				self.line += 1
				return True
		# --- BLOCK CONTENT LINE
		m = self.RE_CONTENT.match(line)
		if m:
			self.onBlockContent(m.group(2) or "")
			self.line += 1
			return True
		# --- BLOCK COMMENT LINE
		m = self.RE_COMMENT.match(line)
		if m:
			self.onComment(m.group(2) or "", line)
			self.line += 1
			return True
		else:
			self.line += 1
			return False

	def onEnd( self ) -> Iterable[Block]:
		"""Called when the input is finished."""
		# TODO: Should extract the result from the blocks
		return (_.end() for _ in self.blockInputs)

	def onBlockStart( self, header:BlockHeader ):
		if self.blockInput:
			self.blockInput.start(header)
			# text = u"\n".join(self.lines)
			# if self.cache.has(text, self.block):
			# 	i = self.blocks.index(self.block)
			# 	b = self.cache.get(text, self.block)
			# 	self.blocks[i] = b
			# else:
			# 	self.block.parseLines(self.lines)
			# 	if text:
			# 		self.cache.set(text, self.block, self.block)
			# self.lines = []
			# self.block = None

	def onBlockContent( self, line:str ):
		# FIXME
		self.blockInput.feed(line)

	def onComment( self, content:str, line:str ):
		pass

	# =========================================================================
	# HELPERS
	# =========================================================================

	def _createBlockInputFromHeader( self, header:BlockHeader ) -> BlockInput:
		block_input = self.mapping.getInputForHeader(header)
		if not block_input:
			raise ValueError(f"No block defined for tag: @{header.name} at line {self.line} in {self.path}")
		else:
			return block_input()

# -----------------------------------------------------------------------------
#
# EMBEDDED PARSER
#
# -----------------------------------------------------------------------------

class EmbeddedParser(Parser):
	"""A parser that processes Polyblock syntax embedded in another language.
	This basically rewrites (or rather, inverts) the given source code
	so that it becomes a polyblock file."""

	# TODO: Should be configurable
	DEFAULT_DELIMITERS = ["#", "//", ";;"]
	POLYBLOCK_EXTENSION = ["block", "polyblock"]
	DELIMITERS = [
		(["c", "cpp", "h", "js", "java"],    ["//", "*"]),
		(["scheme", "scm", "lisp", "tlang"], [";;"]),
		(["sh", "py", "ruby", "sjs", "sg"],  ["#"])
	]

	LINE_DIRECTIVE_HIDE  = 'H'
	LINE_DIRECTIVE_SHOW  = 'S'
	LINE_BLOCK_HEADER    = 'B'
	LINE_BLOCK_COMMENT   = 'c'
	LINE_BLOCK_CONTENT   = 't'
	LINE_RAW_CONTENT     = 'T'

	def __init__( self ):
		super().__init__()

	def parseText( self, text, path ):
		return self.parseLines(self._rewriteLines(text.split("\n"), path), path)

	def parsePath( self, path ):
		with open(path, "rt") as f:
			return self.parseLines(self._rewriteLines(f.readlines(), path), path)

	def _rewriteLines( self, iterator:Iterable[str], path:str ):
		assert path, "The embedded parser needs a path to determine the extension"
		ext = path.rsplit(".",1)[-1]
		if ext in self.POLYBLOCK_EXTENSION:
			yield from iterator
		else:
			delimiters = self.getDelimitersForExt(ext) or self.DEFAULT_DELIMITERS
			# NOTE: We might want to warn when using default delimiters
			previous_line = None
			for line in iterator:
				# We look for the delimiters and see if we have a match
				block_line:Optional[str] = None
				for delim in delimiters:
					if line.startswith(delim):
						# NOTE: We strip the line, which means that the block
						# content NEEDS TO BE TAB-INDENTED. We might want
						# to loosen that constraint. Also, we're stripping the
						# end spaces, which is not always ideal.
						block_line = line[len(delim):].strip()
						# TODO: We might keep the indentation level and use
						# it to strip the content.
						break
				if block_line:
					# We have a line that may belong to a block
					if block_line.startswith("@hidden") or block_line.startswith("@hide"):
						# A hidden directive means we're not showing the rest
						previous_line = self.LINE_DIRECTIVE_HIDE
					elif block_line.startswith("@show"):
						# A show directive means we'll be showing the rest
						previous_line = self.LINE_DIRECTIVE_SHOW
					elif self.RE_HEADER.match(block_line):
						# Is it a block header? If so we pass it as-is
						previous_line = self.LINE_BLOCK_HEADER
						yield block_line
					elif block_line.startswith("#"):
						# Is it a block comment? If so we pass it as-is
						previous_line = self.LINE_BLOCK_COMMENT
						yield block_line
					else:
						# If the previous line is not a block header, then
						# we yield it indented
						if previous_line != "H":
							previous_line = self.LINE_BLOCK_CONTENT
							yield "\t" + block_line
						else:
							# FIXME: Do we ignore the line here
							pass
				elif previous_line == self.LINE_DIRECTIVE_HIDE:
					# We ignore the line as we're in a hide directive
					pass
				else:
					if previous_line != self.LINE_RAW_CONTENT:
						yield "@embed {0}".format(ext)
					previous_line = self.LINE_RAW_CONTENT
					yield "\t" + line

	def getDelimitersForExt( self, ext:str ) -> List[str]:
		"""Returns the list of delimiters that are defined for the
		given file extension in `DELIMITERS`."""
		for exts, seps in self.DELIMITERS:
			if ext in exts:
				return seps
		return []

# EOF - vim: ts=4 sw=4 noet
