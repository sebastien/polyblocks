#!/usr/bin/env python3
#encoding: UTF-8
from pathlib import Path
from xml.etree import ElementTree
import os
from ..transform import Pass
from ..model import InputFile

# -----------------------------------------------------------------------------
#
# XML WRITE PASS
#
# -----------------------------------------------------------------------------

class XMLWriterPass(Pass):
	"""Creates XML outputs from the documents loaded."""

	def __init__( self, path:str ):
		super()
		self.path = Path(path)
		self.xsl  = self.path / "lib/xsl/stylesheet.xsl"

	def onInputFile( self, value:InputFile ):
		output = self.path / value.path.with_suffix(".xml")
		# TODO: Should make it relative
		# print ("Processing", value.path, output)
		root  = value.value
		# We augment the root with useful meta information
		root.attrib["base"] = str(self.path)
		root.attrib["path"] = str(value.path.with_suffix(".xml"))
		root.attrib["id"]   = os.path.splitext(root.attrib["path"])[0]
		#tree  = ElementTree.Element("doc")
		xslpi = ElementTree.ProcessingInstruction("xsl-stylesheet")
		#tree.append(root)
		output.parent.mkdir(parents=True,exist_ok=True)
		# TODO: ElemenTree really sucks at managing proper XML, it's not
		# possible to add the xsl-stylesheet PI at the root 
		# level so we need to do it manually.
		res = ElementTree.tostring(root,method="xml")
		xml_header = b'<?xml version="1.0" encoding="utf8"?>\n'
		xsl_header = f'<?xml-stylesheet type="text/xsl" media="screen" href="{os.path.relpath(self.xsl,output.parent)}"?>\n'.encode("utf8")
		with open(output, "wb") as f:
			f.write(xml_header)
			f.write(xsl_header)
			f.write(res)

# EOF - vim: ts=4 sw=4 noet
