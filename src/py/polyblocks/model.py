#!/usr/bin/env python3
#encoding: UTF-8
import collections
from typing import Dict,List,Any,Optional,Union,TypeVar,Generic,NamedTuple
from .util import xml

__doc__ = """
Defines the content elements for blocks. These elements can be exported
to XML or to JSON-encodable primitives.
"""

T = TypeVar('T')
BlockAttributes = Dict[str,Any]
BlockHeader:NamedTuple = collections.namedtuple('Header', 'name type processors attributes text')

class Block(Generic[T]):

	NAME = "block"

	def __init__( self, value:T ):
		self.name:str = self.NAME
		self.type:str = self.__class__.__name__.rsplit(".",1)[-1].lower()
		self.value    = value
		self.attributes:BlockAttributes = {}

	def setAttributes( self, attributes:BlockAttributes ):
		self.attributes = attributes
		return self

	def toXML( self, document:Any ):
		pass

	def toPrimitive( self ):
		pass

class Document(Block):

	NAME = "document"

class Date(Block):

	NAME = "date"

	def toXML( self, document ):
		d = self.value
		return xml(document, self.name, dict(
			year   = d.year,
			month  = d.month,
			day    = d.day,
			hour   = d.hour,
			minute = d.minute,
			second = d.second,
		))

	def toPrimitive( self ):
		# TODO: Add time zone information
		d = self.value
		res = {}
		res.update(self.attributes)
		res[self.name] = (d.year, d.month, d.day, d.hour, d.minute, d.second)
		return res

class Symbol(Block):

	NAME = "symbol"

	def __init__( self, name:str, type:Optional[str]=None ):
		super().__init__({"name":name, "type":type})

	def toXML( self, document ):
		d = self.value
		return xml(document, self.name, dict(
			name   = d["name"],
			type   = d["type"],
		))

	def toPrimitive( self ):
		res = {}
		res.update(self.attributes)
		res.update(self.value)
		return res

class Anchor(Symbol):

	NAME = "anchor"

class Meta(Block):

	NAME = "meta"

	def toXML( self, document ):
		# TODO: Implement
		return xml(document, self.name, self.attributes)

class Text(Block):

	NAME = "text"

	def toXML( self, document ):
		return xml(document, self.name, self.attributes, self.value)

	def toPrimitive( self ):
		res = {}
		res.update(self.attributes)
		res[self.name] = self.value
		return res

class Line(Text):

	NAME = "line"

class Heading(Text):

	NAME = "heading"

class Code(Text):

	NAME = "code"

class Data(Block[Any]):

	NAME = "data"

	def __init__( self, value:Any, source:Optional[str]=None ):
		super().__init__(value )
		self.source:Optional[str] = source

	def toXML( self, document ):
		# TODO: JSON to XML
		src = xml(document, "source", self.source) if self.source else None
		val = xml(document, "data", self.value)
		return xml(document, self.name or self.NAME, self.attributes, src, val)

	def toPrimitive( self ):
		res = {}
		res.update(self.attributes)
		if self.source:
			res["source"] = self.source
		res["data"]   = self.value
		return res

class XMLTree(Block):

	name = "xml"

class Collection(Block):

	name = "collection"

	# TODO: Can be used to store code and its transpiled versions, we might
	# want to name this differently.
	pass

# EOF - vim: ts=4 sw=4 noet
