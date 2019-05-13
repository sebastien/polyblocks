
class SugarInput(ABlockInput):

	OUTPUT = {
		"imports" : [("module", {"name":str,"path:":str})],
		"source"  : str,
		"errors"  : [str],
	}


# EOF - vim: ts=4 sw=4 noet
