#!/usr/bin/env python3
#encoding: UTF-8
from pathlib import Path
from xml.etree import ElementTree
from ..transform import Pass
from ..model import InputFile, Block, Symbol, Reference
from ..input import TextoFile

# TODO: Inject a TOC per page
# TODO: Inject a list of terms per page
# TODO: Inject a next/previous per page
# TODO: Inject the sitemap per page
class IndexExtractor:
	"""Walks an element tree and creates a hierarchy of symbols, while
	also adding "ref" nodes to the tree."""

	NODE = 0
	SYMBOL = 1

	# TODO: page

	def __init__( self ):
		self.stack:List[Tuple[ElementTree.Element,Symbol]]  = []
		self.blocks:List[Block] = []
		self.block:Optional[Block] = None

	def run( self, value:InputFile, block:Block ):
		self.blocks.append(block)
		self.block = block
		self.walk(value.value)
		self.blocks.pop()
		self.block = None
		return block

	def walk( self, node:ElementTree.Element ):
		symbol = Symbol()
		self.process(node, symbol)
		self.stack.append((node, symbol))
		block = None
		if node.tag == "section":
			block = Block("")
			self.blocks.append(block)
			self.block = block
		for child in node:
			self.walk(child)
		if block:
			self.blocks.pop()
			self.block = self.blocks[-1] if self.blocks else None
		self.stack.pop()
		return self

	def process( self, node:ElementTree.Element, symbol:Symbol ):
		parent, parent_symbol = self.stack[-1] if self.stack else (None, None)
		# We update the block's title
		if node.tag == "title" and parent and parent.tag == "section" and not self.block.name:
			self.block.label = node.text
			self.block.name  = Symbol.ID(node.text)
			self.blocks[-2].add(self.block)
		# We register a symbol as well
		elif node.tag == "title" or (node.tag == "strong" and parent and parent.tag == "list-item"):
			parent_symbol.type   = parent.tag
			parent_symbol.id     = Symbol.ID(node.text)
			parent_symbol.label  = node.text.strip()
			# TODO
			# parent_symbol.parent = self.getParentSymbol()
			# TODO: Should be a unique reference
			parent.attrib["ref"] = "S"
			# NOTE: Sometimes these might be empty
			if parent_symbol.id:
				self.block.register(parent_symbol)
		elif node.tag == "ref":
			ref = Reference(node.text)
			# TODO: Should be a unique reference
			node.attrib["ref"] = "R"
			self.block.register(ref)
		elif node.tag == "link":
			ref = Reference(node.text, node.attrib["target"])
			# TODO: Should be a unique reference
			node.attrib["ref"] = "R"
			self.block.register(ref)
		return self

	# TODO: Not working
	# def getParentSymbol( self ):
	# 	i = len(self.symbols) - 1
	# 	while i >= 0:
	# 		s = self.symbols[i]
	# 		if s.name:
	# 			return s
	# 		else:
	# 			i -= 1
	# 	return None

class IndexPass(Pass):
	"""Introspects the terms and creates an index of any term, symbol, section,
	example, etc."""

	# TODO: Reverse index (pages)
	# TODO: URL listing
	# TODO: assets listing

	def __init__( self ):
		super()
		self.root:Block = Block("")
		self.extractor = IndexExtractor()

	# TODO: When walking, we need to mark the nodes that are the definition
	# of a symbol, and we need to create a hierarchical map.
	def onFile( self, value:InputFile ):
		self.page = self.root.ensure(str(value.path))

	def onTextoFile( self, value:TextoFile ):
		self.onFile(value)
		# TODO: Index extractor should be global, and then symbols/references
		# added to the page.
		block = self.extractor.run(value, self.root.ensure(str(value.path)))
		# NOTE: We inject the structure at the end of the document
		# TODO: This is the OUTLINE
		value.value.append(block.getStructureXML())
		# TODO: Add NEXT/PREVIOUS
		# print (s.symbols)
		# print (s.references)
		# definition-item/title
		# header/title
		# section/title
		# list-item/strong

	def getCatalogueXML( self ):
		node = ElementTree.Element("catalogue")
		node.append(self.root.toXML())
		return node

	def getIndexXML( self ):
		node = ElementTree.Element("index")
		# NOTE: Again, it would be great to be able to query and walk 
		# the model.
		return node

	def getCatalogueXMLString( self ):
		return ElementTree.tostring(self.getCatalogueXML(), method="xml").decode("utf8")

	def getIndexXMLString( self ):
		return ElementTree.tostring(self.getIndexXML(), method="xml").decode("utf8")

# EOF - vim: ts=4 sw=4 noet
