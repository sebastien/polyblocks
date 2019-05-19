from ..inputs import BlockInput
from ..model  import Code

try:
	import paml
except ImportError as e:
	paml = None

class PamlInput( BlockInput ):

	TAG         = "paml"
	DESCRIPTION = "Parses PAML content"

	def init( self ):
		super().init()
		self._parser       = paml.engine.Parser() if paml else None

	def onEnd( self ):
		self._parser.parseString(self.getInputAsString())

# EOF - vim: ts=4 sw=4 noet
