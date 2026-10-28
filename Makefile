# DD2 Project 1, Option 2: Finding Cells Worth Adding
# Required targets (overview 5.1): setup check test all demo clean
#
#   make setup PACK=$HOME/dd2/DD2_Project1_student_pack PDK_ROOT=$PDK_ROOT   (use $HOME, not ~)
#   make check
#   make test
#   make all
#   make demo IN=tests/designs/csa8.v TOP=csa8

SHELL   := /bin/bash
PY      ?= python3
YOSYS   ?= yosys
PACK    ?= $(HOME)/DD2_Project1_student_pack
PDK_ROOT ?= $(HOME)/.ciel
HD_LIB_SRC ?= $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
REQUIRED := cpu8 dsp8 arlet6502 uart_apb risc8 fir10
export YOSYS

.PHONY: setup check test all demo clean selftest hd-classes aigs stats table1 test-aigs

setup:
	$(PY) -m pip install --quiet -r requirements.txt || true
	mkdir -p build/pdk
	ln -sfn "$(HD_LIB_SRC)" build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
	@if [ -d "$(PACK)/given" ]; then ln -sfn "$(abspath $(PACK))/given" build/given; \
	  echo "linked build/given -> $(PACK)/given"; \
	else echo "WARNING: student pack not found at PACK=$(PACK); Table 1 and the AIGs need it"; fi

check:
	@$(PY) -c 'import sys; assert sys.version_info >= (3, 11), sys.version; print("python", sys.version.split()[0])'
	@$(PY) -c 'import numpy; print("numpy", numpy.__version__)'
	@$(YOSYS) -V
	@test -s build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib || (echo "HD Liberty missing: run make setup"; exit 1)
	@$(PY) -c 'import hashlib; print("HD Liberty sha256", hashlib.sha256(open("build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib","rb").read()).hexdigest())'
	@for f in hd_reduced.lib hd_usable.lib scripts/map.sh; do \
	  if [ -e build/given/$$f ]; then echo "ok   given/$$f"; else echo "MISSING given/$$f (make setup PACK=...)"; fi; done

test:
	$(PY) -m unittest -v tests/test_all.py

# regenerate the small test AIGs from our own test designs
test-aigs:
	src/make_aig.sh tests/designs/csa8.v csa8 tests/aig/csa8.aag
	src/make_aig.sh tests/designs/mux_alu4.v mux_alu4 tests/aig/mux_alu4.aag
	$(YOSYS) -q -p "read_verilog tests/designs/csa8.v; synth -flatten -top csa8; async2sync; dffunmap; aigmap; opt_clean; write_aiger tests/aig/csa8.aig"

selftest:
	@mkdir -p results
	set -o pipefail; $(PY) src/redundancy.py selftest | tee results/table4_selftest.txt

hd-classes:
	$(PY) src/hd_class_table.py

# step 1: one AIG per required design (needs the student pack)
aigs:
	@for d in $(REQUIRED); do \
	  top=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import DESIGNS, files; print(DESIGNS['$$d'][0])"); \
	  fl=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import files; print(' '.join(files('$$d')))"); \
	  echo "== $$d (top $$top)"; src/make_aig.sh "$$fl" $$top build/aig/$$d.aag || exit 1; done

# step 2: cuts, their check, and the per-design counts
stats:
	$(PY) src/design_stats.py $(addprefix build/aig/,$(addsuffix .aag,$(REQUIRED)))

table1:
	$(PY) src/table1.py

all: hd-classes selftest aigs stats table1

IN  ?= tests/designs/csa8.v
TOP ?= csa8
demo:
	$(PY) src/demo.py $(IN) $(TOP)

clean:
	rm -rf build/aig build/demo build/smoke build/canon.npz src/__pycache__ tests/__pycache__
