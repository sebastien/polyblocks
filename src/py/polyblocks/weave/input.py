#!/usr/bin/env python3
#encoding: UTF-8
from pathlib import Path
from xml.etree import ElementTree
from .model import InputFile
from .. import process as polyblocks_process

try:
	import texto
except ImportError as e:
	texto = None

# -----------------------------------------------------------------------------
#
# POLYBLOCK FILE
#
# -----------------------------------------------------------------------------

class PolyblockFile(InputFile[ElementTree.ElementTree]):
	"""Abstracts away a Polyblock input file."""

	EXT = [".block", ".tlang"]

	def _load( self, path:Path ):
		res = polyblocks_process(path.read_text(), path.as_posix())
		return ElementTree.fromstring(res)

# -----------------------------------------------------------------------------
#
# TEXTO FILE
#
# -----------------------------------------------------------------------------

class TextoFile(InputFile[ElementTree.ElementTree]):
	"""Abstracts away a Texto input file."""

	EXT = [".txto"]

	def _load( self, path:Path ):
		# TODO: Fail if texto not defined
		status, res = texto.main.run(("-Oxml", path.as_posix()), noOutput=True)
		return ElementTree.fromstring(res)

# EOF - vim: ts=4 sw=4 noet
