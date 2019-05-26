#!/usr/bin/env python3
from typing import Iterable
from .model import Block
import xml.dom
import json

class Writer:

	def __init__( self, **options ):
		self.options = options

	@property
	def hasPretty( self ) -> bool:
		return bool(self.options.get("pretty"))

	def write( self, blocks:Iterable[Block], output ):
		self.onStart(blocks, output)
		for i,block in enumerate(blocks):
			self.onBlock(block, i, output)
		self.onEnd(blocks, output)

	def writeBlock( self, block:Block, output ):
		raise NotImplementedError

class JSONWriter(Writer):

	def onStart( self, block:Block, output ):
		output.write("[")

	def onBlock( self, block:Block, index:int, output ):
		if index > 0:
			output.write(",")
		output.write(json.dumps(block.toPrimitive(), indent=4 if self.hasPretty else None))

	def onEnd( self, block:Block, output ):
		output.write("]")

class XMLWriter(Writer):

	def __init__( self, **options ):
		super().__init__(**options)
		self.dom      = xml.dom.getDOMImplementation()
		self.docuemnt = None
		self.root     = None
		self.meta     = None

	def onStart( self, block:Block, output ):
		self.document = self.dom.createDocument(None, None, None)
		self.root     = self.document.createElementNS(None, "block")
		#self.meta     = self.document.createElementNS(None, "Meta")
		#self.root.appendChild(self.meta)
		# if self.xsl:
		# 	self.xslPI = self.document.createProcessingInstruction("xml-stylesheet", 'type="text/xsl" media="screen" href="{0}"'.format(self.xsl))
		# 	self.document.appendChild(self.xslPI)
		self.document.appendChild(self.root)

	def onBlock( self, block:Block, index:int, output ):
		node = block.toXML(self.document)
		assert node, f"Block did not produce any XML output: {block}"
		if node:
			# TODO: Take care of meta
			self.root.appendChild(node)

	def onEnd( self, block:Block, output ):
		result = self.document.toprettyxml("\t") if self.hasPretty else self.document.toxml()
		output.write(result)

# EOF - vim: ts=4 sw=4 noet
