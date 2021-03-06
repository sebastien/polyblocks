import pickle, os
from   typing import Any,Dict,Optional,Union,Iterable
# NOTE: Document is not defined there
from   xml.dom import Node,getDOMImplementation
from   collections import OrderedDict

class XMLFactory:
	"""Converts primitive values to XML nodes."""

	INSTANCE = None

	@classmethod
	def Get( cls ) -> 'XMLFactory':
		if not cls.INSTANCE:
			cls.INSTANCE = XMLFactory()
		return cls.INSTANCE

	def __init__( self ):
		self.dom      = getDOMImplementation()

	def isAttributeValue( self, value:Any ) -> bool:
		return isinstance(value,str) or isinstance(value,int) or isinstance(value,float) or isinstance(value,bool) or value is None

	def attrs( self, document:'Document', node:Node, attributes:Optional[Union[Dict[str,str],Iterable[str]]]=None ):
		attrs = attributes.items() if isinstance(attributes, dict) or isinstance(attributes, OrderedDict) else enumerate(attributes)
		for name, value in attrs:
			if self.isAttributeValue(value):
				node.setAttribute(name, str(value))
			else:
				node.appendChild(self.node( document, name, value ))
		return node

	def add( self, document, node:Node, child:Node ) -> Node:
		if node.nodeType == Node.TEXT_NODE:
			return node
		elif isinstance(child, dict) or isinstance(child, OrderedDict):
			for k,v in child.items():
				if self.isAttributeValue(v):
					node.setAttributeNS(None, k, str(v))
				else:
					node.appendChild(self.node( document, k, v ))
		elif isinstance(child, str) or isinstance(child, str):
			node.appendChild(document.createTextNode(child))
		elif isinstance(child, list) or isinstance(child, tuple):
			for i,v in enumerate(child):
				node.appendChild(self.node( document, "item", {"index":i}, v))
		elif child:
			node.appendChild(child)
		return node

	def node( self, document:'Document', name:str, *children ) -> Node:
		if name == "#text":
			return document.createTextNode("".join(_ for _ in children))
		else:
			node = document.createElementNS(None, name)
			for i,child in enumerate(children):
				if i == 0 and isinstance(child, dict) or isinstance(child, OrderedDict):
					self.attrs( document, node, child )
				else:
					self.add(document, node, child)
			return node

	def __call__( self, document:'Document', name, *children ):
		return self.node(document, name, *children)

# -----------------------------------------------------------------------------
#
# CACHE
#
# -----------------------------------------------------------------------------

#@symbol cache
class Cache:
	"""A simple self-cleaning cache."""

	CACHE = None
	PATH  = os.path.expanduser("~/.cache/polyblocks")

	@classmethod
	def Ensure(cls) -> 'Cache':
		"""Ensures that there is an instance of the cache configured
		at the default `Cache.PATH`."""
		if not cls.CACHE:
			return Cache(path=cls.PATH)
		else:
			return cls.CACHE

	def __init__( self, path:str ):
		"""Creates the cache at the given location."""
		self.root = os.path.abspath(os.path.normpath(os.path.expanduser(path)))
		assert path
		if not os.path.exists(path):
			os.makedirs(path)

#	# FIXME: Why is there a block here?
#	def key( self, text:str, block:Block ) -> str:
#		"""Gets the key for the given text as processed by the given block."""
#		return self.hash(text) + self.hash(block.key())
#
#	def hash( self, text ):
#		"""Returns the SHA-256 hex digest of the given text."""
#		return hashlib.sha256(text.encode("utf8")).hexdigest()
#
#	def has( self, text:str, block:Block ) -> bool:
#		"""Tells if there is a cache entry for the given text and block."""
#		if not text: return False
#		key = self.key(text, block)
#		return key and os.path.exists(self._path(key))
#
#	def get( self, text:str, block:Block ) -> Block:
#		"""Returns the cache entry for the given text and block."""
#		if not text: return None
#		key = self.key(text, block)
#		if self.has(text, block):
#			with open(self._path(key), "rb") as f:
#				try:
#					return pickle.load(f)
#				except ValueError as e:
#					# We might get an unsupported pickle protocol: 3
#					return
#		return None
#
#	def set( self, text:str, block:Block, value:Any ) -> Any:
#		"""Saves the given `value` for the `(text,block)` entry."""
#		if not text: return text
#		self.clean()
#		key = self.key(text, block)
#		with open(self._path(key), "wb") as f:
#			pickle.dump(value, f)
#		return value
#
	def clean( self, full=False, timeout=60*60*24 ):
		"""Cleans the cache, removing any entry older than timeout (1 day)."""
		now = time.time()
		for _ in list(os.listdir(self.root)):
			p = os.path.join(self.root, _)
			s = os.stat(p)[stat.ST_MTIME]
			if full or (now - s > timeout):
				os.unlink(p)

	def _path( self, key:str ) -> str:
		"""Returns the path for the given key"""
		assert key
		return os.path.join(self.root, key + ".cache")

# -----------------------------------------------------------------------------
#
# HIGH LEVEL API
#
# -----------------------------------------------------------------------------

def xml( document:'Document', name:str, *children ) -> Node:
	"""Wraps `XMLFactory.node` into a simple function."""
	return XMLFactory().Get().node(document, name, *children)

# EOF - vim: ts=4 sw=4 noet
