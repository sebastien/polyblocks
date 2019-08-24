#!/usr/bin/env python3
#encoding: UTF-8
from typing import Union
from ..model import Catalogue, Collection, InputFile

# -----------------------------------------------------------------------------
#
# PASS
#
# -----------------------------------------------------------------------------

class Pass:
	"""Processes a catalogue, a collection or an input file. It is an
	abstract class meant to be specialized to perform specific tasks."""

	def process( self, value:Union[Catalogue,Collection,InputFile] ):
		self.onStart()
		self.walk(value)
		return self.onEnd()

	def onStart( self ):
		pass

	def onEnd( self ):
		return self

	def on( self, value, defaultName ):
		"""Dispatches the given `value` to the handler like
		`onValueClassName` or `on{defaultName}`."""
		handler_name = "on" + value.__class__.__name__
		if hasattr(self, handler_name):
			return getattr(self, handler_name)(value)
		else:
			return getattr(self, "on" + defaultName)(value)

	def walk( self, value:Union[Catalogue,Collection,InputFile] ):
		if isinstance(value, Catalogue):
			return self.walkCatalogue(value)
		elif isinstance(value, Collection):
			return self.walkCollection(value)
		elif isinstance(value, InputFile):
			return self.on(value, "InputFile")
		else:
			raise ValueError(f"Trying to walk an unsupported value: {value}")

	def walkCatalogue( self, value:Catalogue ):
		if self.on(value, "Catalogue") is not False:
			for k,v in value.collections.items():
				if self.walk(v) is False:
					break

	def walkCollection( self, value:Collection ):
		if self.on(value, "Collection") is not False:
			for v in value.files:
				if self.walk(v) is False:
					break

	def onCatalogue( self, value:Catalogue ):
		pass

	def onCollection( self, value:Collection ):
		pass

	def onInputFile( self, value:InputFile ):
		pass

# EOF - vim: ts=4 sw=4 noet
