#!/usr/bin/env python3
#encoding: UTF-8

__doc__ = """
Defines the content elements for blocks. These elements can be exported
to XML or to JSON-encodable primitives.
"""

class Content:

	def toXML( self ):
		pass

	def toPrimitive( self ):
		pass

class Document(Content):
	pass

class Date(Content):
	pass

class Meta(Content):
	pass

class Text(Content):
	pass

class XMLTree(Content):
	pass

class Collection(Content):
	# TODO: Can be used to store code and its transpiled versions, we might
	# want to name this differently.
	pass

# EOF - vim: ts=4 sw=4 noet
