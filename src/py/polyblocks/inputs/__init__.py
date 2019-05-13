#!/usr/bin/env python3
from typing import Dict,List,Any,Optional,Union
from xml.dom import Node
from enum import Enum
import dateutil.parser

class InputStatus(Enum):

	SUCCESS  = 2
	PARTIAL  = 1
	FAILURE  = 0
	EMPTY    = -1

class InputResult:

	def __init__( self ):
		self.input:List[str]    = []
		self.output:List[str]   = []
		self.errors:List[str]   = []
		self.status:InputStatus = InputStatus.EMPTY
		self._value:Any         = None

	@property
	def value( self ):
		return self._value

	def reset( self ):
		self._status =InputStatus.EMPTY
		return self

	def onStart( self, line:str ):
		pass

	def onLine( self, line:str ):
		pass

	def onEnd( self, line:str ):
		pass

class BlockInput:

	TAG:str                  = ""
	DESCRIPTION:str          = ""

	def __init__( self ):
		self.result:InputResult = InputResult()
		self.init()

	def init( self ):
		pass

	def start( self ):
		self.result.reset()

	def feed( self, line:str ):
		self.onLine(line)
		self.result.input.append(line)

	def onStart( self, line:str ):
		pass

	def onLine( self, line:str ):
		pass

	def onEnd( self, line:str ):
		pass

	def getInputAsString( self ) -> str:
		return "\n".join(self.result.input)

class BlockHeaderInput(BlockInput):
	pass

class BlockContentInput(BlockInput):
	pass

class DateInput(BlockHeaderInput):

	def parse( self, text:str ) -> InputResult:
		return InputResult(dateutil.parser.parse(text))

class ListInput(BlockHeaderInput):

	def parse( self, text:str ) -> InputResult:
		return InputResult([_ for _ in (_.strip() for _ in text.split(",")) if _])

# EOF - vim: ts=4 sw=4 noet
