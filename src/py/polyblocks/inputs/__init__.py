#!/usr/bin/env python3
from typing import Dict,List,Any,Optional,Union,TypeVar,Generic,NamedTuple,cast
from ..model import Date,Text,Line,Heading,Meta,Symbol,Anchor,Block,Data,BlockHeader
from xml.dom import Node
from enum import Enum
import dateutil.parser, collections, json

T = TypeVar('T')

# -----------------------------------------------------------------------------
#
# INPUT STATUS
#
# -----------------------------------------------------------------------------

class InputStatus(Enum):

	SUCCESS  = 2
	PARTIAL  = 1
	FAILURE  = 0
	EMPTY    = -1

# -----------------------------------------------------------------------------
#
# BLOCK INPUT
#
# -----------------------------------------------------------------------------

class BlockInput(Generic[T]):
	"""Consumes a list of strings and produces a block
	object with the corresponding content structure.

	A block input acts like a mini parser and can leverage
	the cache to avoid expensive parsing operation
	if the block content has not changed.
	"""

	TAG:str                  = ""
	DESCRIPTION:str          = ""

	def __init__( self ):
		self.init()
		self.inputLines:List[str] = []
		self.header:Optional[BlockHeader] = None

	def init( self ):
		self.inputLines = []
		self.header = None

	def start( self, header:BlockHeader ):
		self.init()
		line = header.text
		self.header = header
		self.onStart(line)
		self.inputLines.append(line)

	def feed( self, line:str ):
		self.onLine(line)
		self.inputLines.append(line)

	def onStart( self, line:str ):
		pass

	def onLine( self, line:str ):
		pass

	def onEnd( self ):
		pass

	def getInputAsString( self ) -> str:
		return "\n".join(self.inputLines)

	def end( self ) -> T:
		self.onEnd()
		return self.postprocess(self.process())

	def process( self ) -> T:
		raise NotImplementedError(f"Missing {self.__class__.__name__}.process implementation")

	def postprocess( self, block:T ) -> T:
		assert self.header
		if self.header.name:
			cast(Block,block).name = self.header.name
		cast(Block,block).setAttributes(self.header.attributes)
		# TODO: Set attributes
		return block

# -----------------------------------------------------------------------------
#
# LINE INPUT
#
# -----------------------------------------------------------------------------

class LineInput(BlockInput[T]):

	def process( self ) -> T:
		return Line(self.getInputAsString())

# -----------------------------------------------------------------------------
#
# HEADING INPUT
#
# -----------------------------------------------------------------------------

class HeadingInput(LineInput[Heading]):

	def process( self ) -> Heading:
		return Heading(self.getInputAsString())

# -----------------------------------------------------------------------------
#
# META INPUT
#
# -----------------------------------------------------------------------------

class MetaInput(LineInput[Meta]):

	def process( self ) -> Meta:
		return Meta(self.getInputAsString())

# -----------------------------------------------------------------------------
#
# DATE INPUT
#
# -----------------------------------------------------------------------------

class DateInput(LineInput[Date]):

	def process( self ) -> Date:
		return Date(dateutil.parser.parse(self.getInputAsString()))

# -----------------------------------------------------------------------------
#
# SYMBOL INPUT
#
# -----------------------------------------------------------------------------

class SymbolInput(LineInput[Symbol]):

	def process( self ) -> Symbol:
		type_name = [_.strip() for _ in self.getInputAsString().strip().split(" ",2)]
		type:Optional[str] = None
		name:Optional[str] = None
		if len(type_name) == 1:
			name = type_name[0]
			type = None
		elif len(type_name) == 2:
			type, name = type_name
		return Symbol(name or "symbol", type)

# -----------------------------------------------------------------------------
#
# ANCHOR INPUT
#
# -----------------------------------------------------------------------------

class AnchorInput(LineInput[Anchor]):

	def process( self ) -> Anchor:
		type_name = [_.strip() for _ in self.getInputAsString().strip().split(" ",2)]
		if len(type_name) == 1:
			name = type_name[0]
			type = None
		else:
			type, name = type_name
		return Anchor(name, type)

# -----------------------------------------------------------------------------
#
# LIST INPUT
#
# -----------------------------------------------------------------------------

class ListInput(LineInput[List[str]]):

	def process( self ) -> List[str]:
		return [_ for _ in (_.strip() for _ in text.split(",")) if _]

# -----------------------------------------------------------------------------
#
# TEXT INPUT
#
# -----------------------------------------------------------------------------

class TextInput(BlockInput[Text]):

	def process( self ) -> Text:
		return Text(self.getInputAsString())

# -----------------------------------------------------------------------------
#
# CODE INPUT
#
# -----------------------------------------------------------------------------

class CodeInput(TextInput):
	pass

# EOF - vim: ts=4 sw=4 noet
