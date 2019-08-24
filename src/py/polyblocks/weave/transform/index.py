#!/usr/bin/env python3
#encoding: UTF-8
from pathlib import Path
from xml.etree import ElementTree
from ..transform import Pass
from ..model import InputFile, Block, Definition, Reference
from ..input import TextoFile

# TODO: Inject a TOC per page
# TODO: Inject a list of terms per page
# TODO: Inject a next/previous per page
# TODO: Inject the sitemap per page

# -----------------------------------------------------------------------------
#
# INDEX PASS
#
# -----------------------------------------------------------------------------

class IndexPass(Pass):
	"""Introspects the terms and definitions defined in the input files and creates
	an index of any term, definition, section, example, etc.
	
	When run on input files, the pass will populate the `root` *block* with
	the extracted definitions/references and sub-blocks, creating a tree of the
	input files and theircontents."""

	# TODO: Reverse index (pages)
	# TODO: URL listing
	# TODO: assets listing

	def __init__( self, extractor=None ):
		super()
		# The data is organized in blocks which will form a tree
		self.root:Block = Block("")
		# The extractor is a pluggable class that extracts information
		# from the given input files.
		self.extractor  = extractor or IndexExtractor()
		self.page:Block = self.root

	# TODO: When walking, we need to mark the nodes that are the definition
	# of a definition, and we need to create a hierarchical map.
	def onFile( self, value:InputFile ):
		"""Creates a page block for the file at the given path."""
		self.page = self.root.ensure(str(value.path))

	def onTextoFile( self, value:TextoFile ):
		"""Specialized method to extract data from a Texto file."""
		self.onFile(value)
		# TODO: Index extractor should be global, and then definitions/references
		# added to the page.
		block = self.extractor.run(value, self.page)
		# NOTE: We *inject* the structure at the end of the TextoFile's XML 
		# content. This will make it possible to run an XSLT transform
		# and generate a per-docuement preview.
		# TODO: The problem is that the documents get bigger
		value.value.append(block.getStructureXML())
		# TODO: Add NEXT/PREVIOUS
		# print (s.definitions)
		# print (s.references)
		# definition-item/title
		# header/title
		# section/title
		# list-item/strong

	def getCatalogueXML( self ):
		"""Creates a `catalogue` XML node, containing the tree of blocks/definitions
		registered."""
		node = ElementTree.Element("catalogue")
		node.append(self.root.toXML())
		return node

	def getIndexXML( self ):
		"""Creates an `index` XML node, containing the alphabetically sorted
		list of definitions and the paths that refer to them."""
		node = ElementTree.Element("index")
		# NOTE: Again, it would be great to be able to query and walk 
		# the model.
		return node

	def getCatalogueXMLString( self ):
		"""Returns the *catalogue* as an UTF8 XML string."""
		return ElementTree.tostring(self.getCatalogueXML(), method="xml").decode("utf8")

	def getIndexXMLString( self ):
		"""Returns the *index* as an UTF8 XML string."""
		return ElementTree.tostring(self.getIndexXML(), method="xml").decode("utf8")


# -----------------------------------------------------------------------------
#
# INDEX EXTRACTOR
#
# -----------------------------------------------------------------------------

class IndexExtractor:
	"""Walks an element tree and creates a hierarchy of definitions, while
	also adding "ref" nodes to the tree."""

	# TODO: page

	def __init__( self ):
		# The stack of XML nodes and the corresponding definition.
		self.stack:List[Tuple[ElementTree.Element,Definition]]  = []
		# The hierarchy of blocks that are being walked
		self.blocks:List[Block] = []
		# The current block being walked
		self.block:Optional[Block] = None

	def run( self, value:InputFile, block:Block ):
		"""Runs the extractor on the given file, using the given `block`
		as the root block. This will call `walk` with the file's XML
		node."""
		# NOTE: The run/walk methods are stateful, so if they fail the 
		# context will be left in an incorrect state.
		self.blocks.append(block)
		self.block = block
		self.walk(value.value)
		self.blocks.pop()
		self.block = None
		return block

	def walk( self, node:ElementTree.Element ):
		"""Walks the given XML node, generating sub blocks and registering
		definitions based on the content."""
		definition = Definition()
		self.process(node, definition)
		self.stack.append((node, definition))
		block = None
		# A <section> node means a new sub block
		if node.tag == "section":
			block = Block("")
			self.blocks.append(block)
			self.block = block
		# We recurse on  chlid nods
		for child in node:
			self.walk(child)
		# If a block was created, we pop the block stack and restore
		# the current block.
		if block:
			self.blocks.pop()
			self.block = self.blocks[-1] if self.blocks else None
		self.stack.pop()
		return self

	def process( self, node:ElementTree.Element, definition:Definition ):
		"""Processes the given node and registers definitions based on the different tags
		that were encoutered."""
		# NOTE: `definition` is unused.
		parent, parent_definition = self.stack[-1] if self.stack else (None, None)
		# We update the block's title
		if not node.text:
			pass
		elif node.tag == "title" and parent and parent.tag == "section" and not self.block.name:
			self.block.label = node.text
			self.block.name  = Definition.ID(node.text)
			self.blocks[-2].add(self.block)
		# We register a definition as well
		elif node.tag == "title" or (node.tag == "strong" and parent and parent.tag == "list-item"):
			parent_definition.type   = parent.tag
			parent_definition.id     = Definition.ID(node.text)
			parent_definition.label  = node.text.strip()
			# TODO
			# parent_definition.parent = self.getParentDefinition()
			# TODO: Should be a unique reference
			parent.attrib["ref"] = "S"
			# NOTE: Sometimes these might be empty
			if parent_definition.id:
				self.block.register(parent_definition)
		elif node.tag == "ref":
			ref = Reference(node.text)
			# TODO: Should be a unique reference
			node.attrib["ref"] = "R"
			self.block.register(ref)
		elif node.tag == "link":
			assert node.text
			ref = Reference(node.text, node.attrib["target"])
			# TODO: Should be a unique reference
			node.attrib["ref"] = "R"
			self.block.register(ref)
		elif node.tag == "definition-item":
			title = next((_ for _ in node if _.tag == "title"), None)
			# TODO: We should define an achor point, maybe
			if title is not None:
				assert title.text
				definition  = Definition(title.text)
				self.block.register(definition)
		else:
			pass
		return self

	# TODO: Not working
	# def getParentDefinition( self ):
	# 	i = len(self.definitions) - 1
	# 	while i >= 0:
	# 		s = self.definitions[i]
	# 		if s.name:
	# 			return s
	# 		else:
	# 			i -= 1
	# 	return None



# EOF - vim: ts=4 sw=4 noet
