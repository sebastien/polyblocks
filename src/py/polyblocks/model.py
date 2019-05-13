#!/usr/bin/env python3
#encoding: UTF-8

class BlockFormat:

	@classmethod
	def Validate( cls, blockFormat, block ):
		pass

class Block:

	TAG:str                  = ""
	DESCRIPTION:str          = ""
	NAME:str                 = ""
	OUTPUT:Dict[str,str]     = {}
	ATTRIBUTES:Dict[str,str] = {}

	def __init__( self ):
		self._name:str = ""
		self._attributes:Dict[str,Any] = {}
		self._lines:Line[str] = []

	@property
	def name( self ):
		return self._name

	@property
	def meta( self ):
		return self._name

	def feed( self, line ):
		raise Exception("By default, blocks do not accept content.")

	def toXML( self ) -> Node:
		pass

	def toJSON( self ) -> Any:
		pass

class BlockInput:

	SUCCESS  = 2
	PARTIAL  = 1
	FAILURE  = 0
	EMPTY    = -1

	def __init__( self ):
		self._input:Line[str]  = []
		self._output:Line[str] = []
		self._errors:Line[str] = []
		self._status = EMPTY

	def feed( self, line:str ):
		pass

# EOF - vim: ts=4 sw=4 noet
