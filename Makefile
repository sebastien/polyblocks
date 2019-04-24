# @title Polyblocks Makefile

# === BUILD ASSETS AND ARTIFACTS ==============================================

SOURCES_TXTO   =$(wildcard *.txto docs/*/.txto docs/*/*.txto docs/*/*/*.txto)
SOURCES_PY     =$(wildcard src/py/*.py src/py/*/*.py src/py/*/*/*.py research/*.py)
SOURCES_PAML   =$(wildcard src/paml/*.paml)
SOURCES_PCSS   =$(wildcard src/pcss/*.pcss)

DIST_XML      =\
	$(patsubst %.txto,dist/%.xml,$(filter docs/%,$(SOURCES_TXTO))) \
	$(patsubst src/py/polyblocks/%.py,dist/sources/%.xml,$(SOURCES_PY))

DIST_XSL      =\
	$(patsubst src/paml/%.xsl.paml,dist/lib/xsl/%.xsl,$(filter %.xsl.paml,$(SOURCES_PAML)))

DIST_CSS      =\
	$(patsubst src/pcss/%.pcss,dist/lib/css/%.css,$(SOURCES_PCSS))

DIST_ALL      =\
	$(DIST_XML) $(DIST_XSL) $(DIST_CSS)

# === SETUP ===================================================================

# General requirements
DIST_ID      :=$(shell hg id | tr '[:space:]' '-' | cut -d- -f1-2)
SAFE_DIST_ID :=$(shell hg id | cut -d' ' -f1 | tr -d '+')
TIMESTAMP     :=$(shell date +'%F')
TIME          :=$(shell date -R)
YEAR          :=$(shell date +'%Y')

# REQ:texto:pip install --user texto
TEXTO         :=texto
# REQ:texto:pip install --user polyblocks
POLYBLOCKS    :=polyblocks
# REQ:texto:pip install --user paml
PAML          :=paml
# REQ:texto:pip install --user --upgrade libparsing ctypes pythoniccss
PCSS          :=pcss

REQUIRED_CMD  :=$(TEXTO) $(POLYBLOCKS) $(PAML) $(PCSS)

# === COLORS ==================================================================
YELLOW        :=$(shell echo `tput setaf 226`)
ORANGE        :=$(shell echo `tput setaf 208`)
GREEN         :=$(shell echo `tput setaf 118`)
BLUE          :=$(shell echo `tput setaf 45`)
CYAN          :=$(shell echo `tput setaf 51`)
RED           :=$(shell echo `tput setaf 196`)
GRAY          :=$(shell echo `tput setaf 153`)
GRAYLT        :=$(shell echo `tput setaf 231`)
REGULAR       :=$(shell echo `tput setaf 7`)
RESET         :=$(shell echo `tput sgr0`)
BOLD          :=$(shell echo `tput bold`)
UNDERLINE     :=$(shell echo `tput smul`)
REV           :=$(shell echo `tput rev`)
DIM           :=$(shell echo `tput dim`)

# Returns the parents/ancestors of the the given $(1) path
# FROM <https://stackoverflow.com/questions/16144115/makefile-remove-duplicate-words-without-sorting#16151140>
uniq           =$(if $1,$(firstword $1) $(call uniq,$(filter-out $(firstword $1),$1)))
log_message    =$(info $(BOLD)$(YELLOW) ●  $(1)$(RESET))
log_rule       =$(info $(BLUE) ┌ $(BOLD)$(1)$(RESET))
log_rule_end   =$(info $(BLUE) ┴ $(1)$(RESET))
log_product    =$(info $(BLUE) ├ $(GREEN)$(1)$(RESET) $(BLUE)→ $(RESET)$@$(RESET))

# -----------------------------------------------------------------------------
#
# RULES
#
# -----------------------------------------------------------------------------

all: $(DIST_ALL) log-rule-all
	$(call log_rule_end)

# -----------------------------------------------------------------------------
#
# PRODUCTS
#
# -----------------------------------------------------------------------------

dist/%.xml: %.txto
	@$(call log_product,dist:txto→xml)
	@mkdir -p `dirname "$@"` ; true
	@$(TEXTO) -Oxml "$<" > "$@"

dist/sources/%.xml: src/py/polyblocks/%.py
	@$(call log_product,dist:py→xml)
	@mkdir -p `dirname "$@"` ; true
	@$(POLYBLOCKS) -Oxml "$<" > "$@"

dist/lib/xsl/%.xsl: src/paml/%.xsl.paml
	@$(call log_product,dist:paml→xsl)
	@mkdir -p `dirname "$@"` ; true
	@$(PAML) "$<" > "$@"

dist/lib/css/%.css: src/pcss/%.pcss
	@$(call log_product,dist:pcss→css)
	@mkdir -p `dirname "$@"` ; true
	@$(PCSS) "$<" > "$@"

# === HELPERS =================================================================

.FORCE:

log-rule-%:
	@$(call log_rule,$*)

print-%:
	@echo "$*="
	@echo "$($*)" | xargs -n1 echo | sort -dr

# EOF - vim: ts=4 sw=4 noet
