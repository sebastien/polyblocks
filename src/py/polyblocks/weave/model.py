#!/usr/bin/env python3
#encoding: UTF-8
from pathlib import Path
from typing import TypeVar,Generic,Any,Optional,List,Dict,Union
from xml.etree import ElementTree
import glob, os, re

# NOTE: This should really be intergrated in polyblocks as the weave module,
# and it makes sense. At the end of the day, polyblocks is all about creating
# a way to structure and manipulate content in blocks, and outputting stuff
# as XML and JSON is a great way to generate content.

# TODO: This is a good candidate for a TLang program

T = TypeVar("T")
Collections = Dict[str,'Collection']
# The goal:

# 1 - Parse texto files and generate a page
# 2 - Parse tlang files and generate a page
# 3 - Index the texto and tlang files
# 4 - Create a sitemap from the texto and tlang files
# 5 - Generate XML/JSON files (ie. block format) from the files

# -----------------------------------------------------------------------------
#
# INPUT FILE
#
# -----------------------------------------------------------------------------

class InputFile(Generic[T]):
	"""An abstract class that reprents a file that can be consumed as
	an input.
	
	Input files mach a set of extensions and produce an XML tree."""

	EXT:List[str] = []

	@classmethod
	def Matches( cls, path:str ) -> bool:
		for _ in cls.EXT:
			if path.endswith(_):
				return True
		return False

	def __init__( self, path:str ):
		self.path = Path(path)
		self._value:Optional[T] = None

	@property
	def name( self ) -> str:
		return self.path.name

	@property
	def value( self ) -> T:
		if self._value is None:
			self.load()
		assert self._value is not None, f"File was loaded into None: {repr(self)}"
		return self._value

	def load( self ):
		self._value = self._load(self.path)
		return self

	def _load( self, path:Path ):
		raise NotImplementedError

	def __repr__( self ):
		return f"({self.__class__.__name__.rsplit('.')[-1]} {repr(self.path.as_posix())})"

# -----------------------------------------------------------------------------
#
# COLLECTION
#
# -----------------------------------------------------------------------------

class Collection:
	"""Defines a collection of paths that will be processed and converted
	into files. The files can then be processed by passes that will
	generate output."""

	FORMATS:Dict[str,Any] = {}

	@classmethod
	def Ensure( cls, name:str, collection:Union['Collection',Union[str,List[str]]] ):
		if isinstance(collection, Collection):
			return collection.named(name)
		elif isinstance(collection, str):
			return Collection(name).add(collection)
		else:
			return Collection(name).add(*collection)

	@classmethod
	def Register( cls, *classes:Any ):
		for c in classes:
			for e in c.EXT:
				cls.FORMATS[e] = c

	@classmethod
	def File( cls, path:str ) -> Optional['InputFile']:
		i = path.rindex(".")
		if i == -1:
			return None
		else:
			ext = path[i:]
			c = cls.FORMATS.get(ext)
			return c(path) if c else None

	def __init__( self, name:str ):
		self.name = name
		self.files:List[InputFile] = []

	def named( self, name:str ):
		self.name =  name
		return self

	def add( self, *patterns ):
		for pattern in patterns:
			for p in glob.glob(pattern):
				f = Collection.File(p)
				if f:
					self.files.append(f)
		return self

	def __repr__( self ):
		return f"(Collection '{self.name} {' '.join(repr(_) for _ in self.files)})"

# -----------------------------------------------------------------------------
#
# CATALOGUE
#
# -----------------------------------------------------------------------------

class Catalogue:
	"""A catalogue is a set of collections."""

	def __init__( self, collections:Optional[Collections]=None ):
		self.collections:Collections = dict((k,Collection.Ensure(k, v)) for k,v in (collections or {}).items())

	def __repr__( self ):
		return f"(Catalogue {' '.join(repr(_) for _ in self.collections.values())})"

class Symbol:

	@classmethod
	def Normalize( cls, name:str ):
		return re.sub("\s+", " ", name.lower()).strip()

	@classmethod
	def ID( cls, name:str ):
		return re.sub("[^\w\d_]+", "-", name.lower().strip())

	def __init__( self ):
		# FIXME: The difference between id and name should be clarified
		# and made consistent.
		self.id     = None
		self.label  = None
		self.type   = None
		self.parent:Optional[Block]  = None
		self.tags   = []
		# Should be the URL of the symbol
		self.origin = None

	def __repr__( self ):
		return f"(symbol \"{self.id}\" (@ (name \"{self.label}\")))"

	def toXML( self ) -> ElementTree.Element:
		node = ElementTree.Element("symbol")
		node.attrib["id"] = self.id
		node.attrib["label"] = self.label
		node.attrib["type"] = self.type
		if self.parent:
			node.attrib["parent"] = self.parent.path
		return node

class Reference:

	def __init__( self, label, target=None ):
		self.id       = target or Symbol.ID(label)
		self.label    = label
		self.origin   = None
		self.parent:Optional[Block]  = None

	def __repr__( self ):
		return f"(ref \"{self.id}\" (@ (label \"{self.label}\")))"

	def toXML( self ) -> ElementTree.Element:
		node = ElementTree.Element("ref")
		node.attrib["id"] = self.id
		node.attrib["label"] = self.label
		if self.parent:
			node.attrib["parent"] = self.parent.path
		return node

class Block:
	"""A block represents a structural element, such as a page, or
	even sections within a document."""

	def __init__( self, name:str, title:Optional[str]=None ):
		self.name = name
		self.title:Optional[str] = title
		self.parent:Optional[Block] = None
		self.children:Dict[str,Block] = {}
		self.attributes:Dict[str,str] = {}
		# This is meta information about the contents
		self.symbols:Dict[str,List[Symbol]] = {}
		self.references:Dict[str,List[Reference]] = {}

	@property
	def path( self ) -> str:
		return self.parent.path + "/" + self.name if self.parent else self.name

	def register( self, value:Union[Symbol,Reference] ) -> Union[Symbol,Reference]:
		value.parent = self
		if isinstance(value, Symbol):
			self.symbols.setdefault(value.id,[]).append(value)
		elif isinstance(value, Reference):
			self.references.setdefault(value.id,[]).append(value)
		else:
			raise ValueError(f"Unsupported value: {value}")
		return value

	def add( self, block:'Block' ) -> 'Block':
		assert block.name not in self.children
		self.children[block.name] = block
		block.parent = self
		return block

	def resolve( self, path:str ):
		block = self
		for p in path.split("/"):
			if p not in block.children:
				return None
			block = block.children[p]
		return block

	def ensure( self, path:str ):
		block = self
		for p in path.split("/"):
			if p not in block.children:
				block.add(Block(p))
			block = block.children[p]
		return block

	def walk( self, callback ):
		if callback(self) is False:
			return False
		for child in self.children.values():
			if child.walk(callback) is False:
				return False
		return True

	def getStructureXML( self ) -> ElementTree.Element:
		def make_children(block):
			node = ElementTree.Element("block")
			node.attrib["path"] = block.path
			node.attrib["name"] = block.name
			for child in block.children.values():
				node.append(make_children(child))
			return node
		node = ElementTree.Element("structure")
		node.append(make_children(self))
		return node

	def toXML( self ) -> ElementTree.Element:
		node = ElementTree.Element("block")
		for v,k in self.attributes.items():
			node.attrib[k] = v
		name, ext = os.path.splitext(self.name)
		node.attrib["path"] = self.path
		node.attrib["name"] = name
		node.attrib["ext"]  = ext.replace(".","")
		if self.parent:
			node.attrib["parent"]  = self.parent.path
		# We add the structure
		#node.append(self.getStructureXML())
		for k in self.children:
			node.append(self.children[k].toXML())
		for k,ls in self.symbols.items():
			n = ElementTree.Element("definitions")
			n.attrib["name"] = k
			for sym in ls:
				n.append(sym.toXML())
			node.append(n)
		for k,lr in self.references.items():
			n = ElementTree.Element("references")
			n.attrib["name"] = k
			for ref in lr:
				n.append(ref.toXML())
			node.append(n)

		return node

	def toXMLString( self ) -> str:
		return ElementTree.tostring(self.toXML(), method="xml").decode("utf8")

# EOF - vim: ts=4 sw=4 noet
