from ..inputs import BlockInput
from ..model  import Data
import json

# -----------------------------------------------------------------------------
#
# JSON INPUT
#
# -----------------------------------------------------------------------------

class JSONInput( BlockInput ):

	TAG         = "json"
	DESCRIPTION = "Parses JSON content"
	OUTPUT      = Data

	def init( self ):
		super().init()

	def onEnd( self ):
		# TODO: Error handling
		data = json.loads(self.getInputAsString())
		return Data(data)

# EOF - vim: ts=4 sw=4 noet
