import pandas as pd
import re
from pathlib import Path

def make_disease_code_tree():
	# Each branch in the tree is indexed by an abbreviation piece (pieces being e.g. "ADHD" and "RC" in "ADHD-RC")
	# Each node has a "value" entry and/or a "children" entry
	# The value stores the full name of the disease that's identified by the node's path in the tree
	# The children represent all disease abbreviations that have the node's path as a prefix
	source_path = Path(__file__, "disease_abbrev_mapping.tsv")
	df = pd.read_csv(source_path, sep="\t", header=0, keep_default_na=False)
	tree = {}
	node = None
	for abbrev, name in df.itertuples(index=False):
		node = tree
		for piece in abbrev.split("-"):
			if not "children" in node:
				node["children"] = {}
			if not piece in node["children"]:
				node["children"][piece] = {}
			node = node["children"][piece]
		node["value"] = name
	return tree

# Initialize tree so that disease abbreviations can be identified piece-by-piece and distinguished from other consent code symbols
disease_code_tree = make_disease_code_tree()

consent_symbol_defs_list = [
	{"name": "NRES", "class": "primary", "param": "none", "short": "No restrictions", "long": "No restrictions on data use."},
	{"name": "GRU", "class": "primary", "param": "none", "short": "General research use and clinical care", "long": "For health/medical/biomedical purposes, including the study of population origins or ancestry."},
	{"name": "HMB", "class": "primary", "param": "none", "short": "Health/medical/biomedical research and clinical care", "long": "Use of the data is limited to health/medical/biomedical purposes; does not include the study of population origins or ancestry."},
	{"name": "DS", "class": "primary", "param": "required", "short": "Disease-specific research and clinical care", "long_with_param": "Use of the data must be related to []."},
	{"name": "POA", "class": "primary", "param": "none", "short": "Population origins/ancestry research", "long": "Use of the data is limited to the study of population origins or ancestry."},
	{"name": "RS", "class": "secondary", "param": "required", "short": "Other research-specific restrictions", "long_with_param": "Use of the data is limited to studies of research type \"[]\"."},
	{"name": "RUO", "class": "secondary", "param": "none", "short": "Research use only", "long": "Use of data is limited to research purposes (e.g., does not include its use in clinical care)."},
	{"name": "NMDS", "class": "secondary", "param": "none", "short": "No \"general methods\" research", "long": "Use of the data includes methods development research (e.g., development of software or algorithms) ONLY within the bounds of other data use limitations."},
	{"name": "GSO", "class": "secondary", "param": "none", "short": "Genetic studies only", "long": "Use of the data is limited to genetic studies only (i.e., no \"phenotype-only\" research)."},
	{"name": "NPU", "class": "secondary", "param": "none", "short": "Not-for-profit use only", "long": "Use of the data is limited to not-for-profit organizations."},
	{"name": "PUB", "class": "secondary", "param": "none", "short": "Publication required", "long": "Requestor agrees to make results of studies using the data available to the larger scientific community."},
	{"name": "COL", "class": "secondary", "param": "none", "short": "Collaboration required", "long": "Requestor must agree to collaboration with the primary study investigator(s)."},
	{"name": "IRB", "class": "secondary", "param": "none", "short": "Ethics approval required", "long": "Requestor must provide documentation of local IRB/REC approval."},
	{"name": "GS", "class": "secondary", "param": "required", "short": "Geographical restrictions", "long_with_param": "Use of the data is limited to within geographic region \"[]\"."},
	{"name": "MOR", "class": "secondary", "param": "required", "short": "Publication moratorium/embargo", "long_with_param": "Requestor agrees not to publish results of studies until the date []."},
	{"name": "TS", "class": "secondary", "param": "required", "short": "Time limits on use", "long_with_param": "Use of data is approved for [] months."},
	{"name": "US", "class": "secondary", "param": "none", "short": "User-specific restrictions", "long": "Use of data is limited to use by approved users."},
	{"name": "PS", "class": "secondary", "param": "none", "short": "Project-specific restrictions", "long": "Use of data is limited to use within an approved project."},
	{"name": "IS", "class": "secondary", "param": "none", "short": "Institution-specific restrictions", "long": "Use of data is limited to use within an approved institution."},
	{"name": "MDS", "class": "secondary", "param": "none", "short": "", "long": "Use of the data includes methods development research (e.g., development of software or algorithms)"},
]

# Convert symbol definitions to dict indexed by symbol name
consent_symbol_defs = {d["name"]: d for d in consent_symbol_defs_list}

# Symbols that have output fields for whether they appear or not
bool_field_consent_symbols = ["NRES", "GRU", "HMB", "IRB", "PUB", "COL", "NPU", "MDS", "GSO"]

def generateConsentDescriptions(code):
	if code == "" or code == "TBD" or code == "NA" or code == "Unspecified":
		return {
			**{s: "Unspecified" for s in bool_field_consent_symbols},
			"DS": "Unspecified",
			"diseaseText": "Unspecified",
			"consentLongName": "Unspecified",
			"consentTitle": "Unspecified"
		}
	
	# Convert consent code to a list of dicts representing symbols, and a list of the separators between the symbols
	# Known symbols are taken from consent_symbol_defs, and unknown symbols are classed as "parameter"
	separators, symbols = zip(*re.findall("(^|-|_|,\\s*)([^-_,]*)", code))
	symbols = [consent_symbol_defs.get(symbol, {"name": symbol, "class": "parameter"}) for symbol in symbols]
	
	short = ""
	long = ""
	error = ""
	i = 0
	current_class = "primary"
	short_has_parens = False
	
	# Initialize symbol-specific output fields
	descriptions = {s: False for s in bool_field_consent_symbols}
	descriptions["DS"] = ""
	descriptions["diseaseText"] = ""
	
	# Variables used locally in the loop
	j = None
	tree_node = None
	param_text = None
	full_param_text = None
	long_param_text = None

	# Loop over the consent code's symbols
	# The entire consent code will be processed even if there's unrecognized syntax, in order to find values for the symbol-specific fields
	while i < len(symbols):
		# Check that the current symbol has the expected class
		if symbols[i]["class"] != current_class:
			if symbols[i]["class"] == "parameter":
				error = error or "Unknown symbol \"" + symbols[i]["name"] + "\""
			else:
				error = error or "Invalid position for " + symbols[i]["class"] + " symbol \"" + symbols[i]["name"] + "\""
			i += 1
		else:
			if symbols[i]["name"] in bool_field_consent_symbols:
				# Update boolean output field
				descriptions[symbols[i]["name"]] = True
			
			# Add text that's consistent regardless of parameter
			if current_class == "primary":
				short += symbols[i]["short"]
			else:
				if short[-1] != "(":
					short += ", "
				short += symbols[i]["name"]
				long += " "

			if symbols[i]["param"] == "none":
				# Add text for symbol without a parameter
				if current_class == "primary" and len(symbols) > i + 1:
					short += " ("
					short_has_parens = True
				long += symbols[i]["long"]
			else:
				# Parse parameter
				j = i
				# If the symbol is "DS", use the disease code tree
				tree_node = disease_code_tree if symbols[j]["name"] == "DS" else None
				param_text = ""
				# Parse symbols as part of the parameter as long as they're in the tree or have class "parameter"
				while i + 1 < len(symbols) and (symbols[i + 1]["class"] == "parameter" or (tree_node and "children" in tree_node and symbols[i + 1]["name"] in tree_node["children"])):
					i += 1
					if i > j + 1:
						param_text += separators[i]
					param_text += symbols[i]["name"]
					if tree_node:
						if "children" in tree_node:
							tree_node = tree_node["children"].get(symbols[i]["name"])
						else:
							tree_node = None
				if i == j: # If i hasn't changed, there's a missing parameter
					error = error or "Missing required parameter to \"" + symbols[i]["name"] + "\""
				full_param_text = tree_node["value"] if tree_node and "value" in tree_node else None
				long_param_text = full_param_text or ("disease \"" + param_text + "\"" if symbols[j]["name"] == "DS" else param_text)
				# Add symbol and parameter text
				if current_class == "primary":
					short += " ("
					short_has_parens = True
				else:
					short += separators[j + 1]
				short += param_text
				long += symbols[j]["long_with_param"].replace("[]", long_param_text)
				# If the symbol is "DS", update the disease-related output fields
				if symbols[j]["name"] == "DS":
					descriptions["DS"] = param_text
					if full_param_text:
						descriptions["diseaseText"] = full_param_text

			i += 1
			
			# Update expected class for the next symbol
			if current_class == "primary":
				current_class = "secondary"
		
	if short_has_parens:
		short += ")"
	
	descriptions["consentLongName"] = long if error == "" else "ERROR: " + error
	descriptions["consentTitle"] = short if error == "" else "ERROR"
	
	return descriptions