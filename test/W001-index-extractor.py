from polyblocks.weave.model           import Collection, Catalogue
from polyblocks.weave.input           import TextoFile, PolyblockFile
from polyblocks.weave.transform.xml   import XMLWriterPass
from polyblocks.weave.transform.index import IndexPass
import os.path

__doc__ = """
Ensures that symbols are properly extracted form texto and block files
"""

Collection.Register(TextoFile, PolyblockFile)
catalogue = Catalogue(
	collections = {
		"texto":os.path.join(os.path.dirname(__file__), "data/*.txto")
	}
)

index = IndexPass().process(catalogue)
# TODO: Assert the presence/absence of stuff
print (index.root)
print (index.root.toXMLString())

# EOF - vim: ts=4 sw=4 noet
