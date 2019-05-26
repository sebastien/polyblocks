from ..inputs import BlockInput
from ..model  import Data

try:
	import hjson
except ImportError as e:
	hjson = None

class HJSONInput( BlockInput[Data] ):

	TAG         = "hjson"
	DESCRIPTION = "Parses HJSON content"
	OUTPUT      = Data

	def init( self ):
		super().init()

	def process( self ) -> Data:
		# TODO: Error handling
		src  = self.getInputAsString()
		data = hjson.loads(src)
		return Data(data, src)

# EOF - vim: ts=4 sw=4 noet
