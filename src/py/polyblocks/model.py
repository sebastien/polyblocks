#!/usr/bin/env python3
#encoding: UTF-8

from .util import xml

__doc__ = """
Defines the content elements for blocks. These elements can be exported
to XML or to JSON-encodable primitives.
"""

class Block:

	def __init__( self, date ):
		self.value = date

	def toXML( self, document:'XMLDocument' ):
		pass

	def toPrimitive( self ):
		pass

class Document(Block):
	pass

class Date(Block):

	def toXML( self, document ):
		d = self.value
		return xml(document, "date", dict(
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
		return (d.year, d.month, d.day, d.hour, d.minute, d.second)

class Meta(Block):

	def toXML( self, document ):
		# TODO: Implement
		return xml(document, "meta")

class Text(Block):

	def toXML( self, document ):
		return xml(document, "text", self.value)

	def toPrimitive( self ):
		return {"text":self.value}

class Line(Text):
	pass

class Heading(Text):
	pass

class Code(Text):
	pass

class XMLTree(Block):
	pass

class Collection(Block):
	# TODO: Can be used to store code and its transpiled versions, we might
	# want to name this differently.
	pass

# EOF - vim: ts=4 sw=4 noet
