import pickle

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
		self.root = os.path.asbpath(os.path.normpath(os.path.expanduser(path)))
		assert path
		if not os.path.exists(path):
			os.makedirs(path)

	# FIXME: Why is there a block here?
	def key( self, text:str, block:Block ) -> str:
		"""Gets the key for the given text as processed by the given block."""
		return self.hash(text) + self.hash(block.key())

	def hash( self, text ):
		"""Returns the SHA-256 hex digest of the given text."""
		return hashlib.sha256(text.encode("utf8")).hexdigest()

	def has( self, text:str, block:Block ) -> bool:
		"""Tells if there is a cache entry for the given text and block."""
		if not text: return False
		key = self.key(text, block)
		return key and os.path.exists(self._path(key))

	def get( self, text:str, block:Block ) -> Block:
		"""Returns the cache entry for the given text and block."""
		if not text: return None
		key = self.key(text, block)
		if self.has(text, block):
			with open(self._path(key), "rb") as f:
				try:
					return pickle.load(f)
				except ValueError as e:
					# We might get an unsupported pickle protocol: 3
					return
		return None

	def set( self, text:str, block:Block, value:Any ) -> Any:
		"""Saves the given `value` for the `(text,block)` entry."""
		if not text: return text
		self.clean()
		key = self.key(text, block)
		with open(self._path(key), "wb") as f:
			pickle.dump(value, f)
		return value

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

# EOF - vim: ts=4 sw=4 noet
