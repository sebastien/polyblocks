#!/usr/bin/env python3
#encoding: UTF-8
from .model  import Block
from .inputs import LineIpnut, DateInput, ListInput
from .inputs.paml import PamlInput
from .util   import Cache
from typing  import Optional,List,Iterator,Dict,NamedTuple
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

	BLOCKS = {
		"@title"    : LineInput.As("title"),
		"@subtitle" : LineInput.As("subtitle"),
		"@date"     : DateInput,
		"@created"  : DateInput.As("created"),
		"@updated"  : DateInput.As("updated"),
		"@tags"     : ListInput.As("tags"),
	}

	INPUTS = {
		"paml"      : PamlInput,
		# "pcss"      : PCSSInput,
		# "texto"     : TextoInput,
		# "sugar"     : SugarInput,
	}

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------

Header:NamedTuple = collections.namedtuple('Header', 'name type processors attributes line')

#@symbol polyblocks.parser.Parser
class Parser:
	"""Parses the polyblock text format, using the `Mapping` to define
	which the block names and input formats are available."""

	# A block header is like `@NAME:TYPE|P0,P1 CONTENT… 
	RE_HEADER   = re.compile("^@(\w+)(:\w+)?(\|[\w\-_]+(,[\w\-_]+)?)(\s+.*)?\s*$")
	RE_CONTENT  = re.compile("^(\t(.*)|\s*)$")
	RE_COMMENT  = re.compile("^#.*$")

	def __init__( self ):
		self.block:Optional[Block] = None
		self.lines:List[str]       = []
		self.rawLines:List[str]    = None
		self.blocks:List[Block]    = []
		self.path:Optional[str]    = None
		self.line                  = 0
		self.cache                 = Cache.Ensure()

	def parseText( self, text:str, path:Optional[str]=None ) -> List[Block]:
		"""Parses the given `text`, loaded from the given `path` (optional).
		The text is going to be split into lines and fed to  `parseIterator`."""
		return self.parseIterator(text.split("\n"), path)

	def parsePath( self, path:str ) -> List[Block]:
		"""Parses the text at the given `path`."""
		with open(path, "rt") as f:
			return self.parseIterator(f.readlines(), path)

	def parseLines( self, lines:Iterator[str], path:Optional[str] ) -> List[Block]:
		"""Parses the given `lines`, coming from a file at the given
		`path`."""
		self.onStart(path)
		for line in lines:
			self.onLine(line)
		self.onEnd()
		return self.blocks

	# =========================================================================
	# HEADER PARSING
	# =========================================================================

	def parseHeaderLine( self, line:str ) -> Optional[Header]:
		match      = self.RE_HEADER.match(line)
		if not match: return None
		type       = match.group(2) or match.group(1),
		name       = match.group(1) if not match.group(2) else None
		processors = [_.strip() for _ in match.group(2)[1:].split(",")] if match.group(2) else []
		rest       = match.group(4)
		line       = rest
		attributes = {}
		i = line.find("{")
		j = line.rfind("{")
		if i >= 0 and i < j:
			line = rest[:i]
			attributes = self.parseHeaderAttributes(rest[i+1:j-1])
		return Header(name,type,processors,attributes,line)

	def parseHeaderAttributes( self, line:str ) -> Dict[str,Any]:
		"""A simple parser that extract (key,value) from a string like
		`KEY=VALUE,KEY="VALUE\"VALUE",KEY='VALUE\'VALUE'`"""
		offset = 0
		result:Dict[str,Any] = dict()
		while offset < len(text):
			equal = text.find("=", offset)
			if equal == -1:
				comma = text.find(",",offset)
				if comma == -1:
					sep = len(text)
				else:
					sep = comma
			else:
				sep = equal
			name   = text[offset:sep]
			offset = sep + 1
			if offset >= len(text):
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
			result[name.strip] = value or True
		return result

	# =========================================================================
	# PARSING EVENTS
	# =========================================================================

	def onStart( self, path:Optional[str]=None ):
		"""Called when the parsing starts, initializes the parser state."""
		self.line      = 0
		self.path      = path
		self.lines     = []
		self.rawLines  = []
		self.block     = None

	def onLine( self, line:str ) -> bool:
		"""Called when a line is fed into the parser."""
		# NOTE: We need to make sure the input is unicode
		self.line += 1
		# --- BLOCK LINE
		# If the line starts with `@` then it's a block declaration
		if line.startswith("@"):
			# We parse the header line, 
			header = self.parseHeaderLine(m)
			if not header:
				# TODO: We have a potentially malformed line, we should
				# surface it to the user.
				pass
			else:
				# We create a block from the header
				block  = self._createBlockFromHeader(header)
				# We notify that a new block is starting, which by default
				# flushes all parsed lines and assigns them to the current block
				self.onBlockStart()
				# The new block becomes the current block
				self.block = block
				block._addLines([line])
				if block not in self.blocks:
					self.blocks.append(block)
				return True
		# --- BLOCK CONTENT LINE
		m = RE_CONTENT.match(line)
		if m:
			self.onBlockContent(m.group(2) or "", line)
			return True
		# --- BLOCK OCMMENT LINE
		m = RE_COMMENT.match(line)
		if m:
			self.onComment(m.group(2) or "", line)
			return True
		else:
			return False

	def onEnd( self ):
		"""Called when the input is finished."""
		self.onBlockStart()

	def onBlockStart( self ):
		if self.block:
			self.block._addLines(self.rawLines)
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
			self.rawLines = []
			self.block = None

	def onBlockContent( self, content:str, line:str ):
		self.lines.append(m.group(2) or "")
		self.rawLines.append(line)

	def onComment( self, content:str, line:str ):
		pass

	# =========================================================================
	# HELPERS
	# =========================================================================

	def _createBlock( self, name:str, data:str, attrs:Dict[str,Any], binding:str ) -> Block:
		block_class = self.BLOCKS.get(name)
		if not block_class:
			raise Exception("No block defined for tag: `@{0}` at line {1} in {2}".format(name, self.line, self.path))
		else:
			return block_class(name=name, data=data, attributes=attrs, binding=binding, path=self.path)


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
	DELIMITERS = [
		(["c", "cpp", "h", "js", "java"],    ["//", "*"]),
		(["scheme", "scm", "lisp", "tlang"], [";;"]),
		(["sh", "py", "ruby", "sjs", "sg"],  ["#"])
	]

	def __init__( self ):
		super().__init__()

	def parseText( self, text, path ):
		return self.parseIterator(self._rewriteIterator(text.split("\n"), path), path)

	def parsePath( self, path ):
		with open(path, "rt") as f:
			return self.parseIterator(self._rewriteIterator(f.readlines(), path), path)

	def _rewriteIterator( self, iterator, path ):
		ext        = path.rsplit(".",1)[-1]
		if ext in ("block", "polyblock"):
			yield from iterator
		else:
			delimiters = self.getDelimitersForExt(ext)
			previous_line = None
			for line in iterator:
				for delim in delimiters:
					if line.startswith(delim):
						line = line[len(delim):].strip()
						if line.startswith("@hidden") or line.startswith("@hide"):
							previous_line = "H"
						elif line.startswith("@show"):
							previous_line = "S"
						elif RE_BLOCK.match(line):
							previous_line = 'B'
							yield line
						elif line.startswith("#"):
							previous_line = 'c'
							yield line
						else:
							if previous_line != "H":
								previous_line = 't'
								yield "\t" + line
					elif previous_line == "H":
						pass
					else:
						if previous_line != 'T':
							yield "@embed {0}".format(ext)
						previous_line = 'T'
						yield "\t" + line

	def getDelimitersForExt( self, ext:str ) -> List[str]:
		for exts, seps in self.DELIMITERS:
			if ext in exts:
				return seps
		return []

# EOF - vim: ts=4 sw=4 noet
