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
ABC     ?= yosys-abc
PACK    ?= $(HOME)/DD2_Project1_student_pack
PDK_ROOT ?= $(HOME)/.ciel
TUT2    ?= $(abspath ../tutorials/tut2/student)
TUT4    ?= $(abspath ../tutorials/tut4)
HD_LIB_SRC ?= $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
REQUIRED := cpu8 dsp8 arlet6502 uart_apb risc8 fir10
# every design the flow analyses, maps and ranks on (handout section 3)
ANALYSED := $(REQUIRED) spm mul
export YOSYS ABC

.PHONY: setup check test all demo clean selftest hd-classes aigs stats table1 test-aigs area-model candidates cell-requests liberty-with-new-cells mapping mapping-equivalence new-cell-verilog-sims gate-level-testbenches table5-estimated baseline-mapping-spm-mul

setup:
	$(PY) -m pip install --quiet -r requirements.txt || true
	mkdir -p build/pdk
	ln -sfn "$(HD_LIB_SRC)" build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
	ln -sfn "$(dir $(HD_LIB_SRC))../verilog" build/pdk/verilog
	@if [ -d "$(PACK)/given" ]; then ln -sfn "$(abspath $(PACK))/given" build/given; \
	  echo "linked build/given -> $(PACK)/given"; \
	else echo "WARNING: student pack not found at PACK=$(PACK); Table 1 and the AIGs need it"; fi
	@for t in 2 4; do d=$$([ $$t = 2 ] && echo "$(TUT2)" || echo "$(TUT4)"); \
	  if [ -d "$$d" ]; then ln -sfn "$$(cd "$$d" && pwd)" build/tut$$t; echo "linked build/tut$$t -> $$d"; \
	  else echo "WARNING: Tutorial $$t not found at TUT$$t=$$d; SPM and mul need it"; fi; done

check:
	@$(PY) -c 'import sys; assert sys.version_info >= (3, 11), sys.version; print("python", sys.version.split()[0])'
	@$(PY) -c 'import numpy; print("numpy", numpy.__version__)'
	@$(YOSYS) -V | grep "^Yosys 0\.33 " || (echo "need Yosys 0.33 (handout Table 1): run in the student pack image dd2-layout-tools"; exit 1)
	@test -s build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib || (echo "HD Liberty missing: run make setup"; exit 1)
	@$(PY) -c 'import hashlib; print("HD Liberty sha256", hashlib.sha256(open("build/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib","rb").read()).hexdigest())'
	@for f in hd_reduced.lib hd_usable.lib scripts/map.sh; do \
	  if [ -e build/given/$$f ]; then echo "ok   given/$$f"; else echo "MISSING given/$$f (make setup PACK=...)"; fi; done

test:
	$(PY) -m unittest -v tests/test_all.py tests/test_candidates.py tests/test_abc_after.py tests/test_liberty_with_new_cells.py tests/test_mapping_equivalence.py tests/test_gate_level_testbenches.py tests/test_final_set.py

# regenerate the small test AIGs from our own test designs
test-aigs:
	src/make_aig.sh tests/designs/csa8.v csa8 tests/aig/csa8.aag
	src/make_aig.sh tests/designs/mux_alu4.v mux_alu4 tests/aig/mux_alu4.aag

selftest:
	@mkdir -p results
	set -o pipefail; $(PY) src/redundancy.py selftest | tee results/table4_selftest.txt

hd-classes:
	$(PY) src/hd_class_table.py

# step 1: one AIG per design (required, SPM, mul), and the same graph after ABC strash; dch (needs the student pack)
aigs:
	@for d in $(ANALYSED); do \
	  top=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import DESIGNS, files; print(DESIGNS['$$d'][0])"); \
	  fl=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import files; print(' '.join(files('$$d')))"); \
	  echo "== $$d (top $$top)"; src/make_aig.sh "$$fl" $$top build/aig/$$d.aag || exit 1; \
	  src/abc_after.sh build/aig/$$d.aig build/aig/$${d}_abc.aig || exit 1; done

# step 2: cuts, their check, and the per-design counts, before and after ABC (handout 9.2)
stats:
	$(PY) src/design_stats.py $(foreach d,$(ANALYSED),build/aig/$(d).aag build/aig/$(d)_abc.aig)

table1:
	$(PY) src/table1.py

# step 6: the area model, fitted to HD's x1 cells (results/area_model.json)
area-model:
	$(PY) src/costmodel.py fit

# steps 3-7: classify cuts against HD, cost, estimate and rank the candidates.
# Needs `make aigs` and `make table1` first (the Table 1 logs give the baseline
# area per AND node). GROUP is your group tag in the cell names: dd2_<GROUP>__...
GROUP ?= gb2
# baseline mappings of SPM and mul, which have no Table 1 log: the ranking reads their area per AND
baseline-mapping-spm-mul:
	$(PY) src/map_with_and_without_new_cells.py --designs spm,mul --baseline-only

candidates: area-model baseline-mapping-spm-mul
	$(PY) src/candidates.py --group $(GROUP)

# step 8, part 1: one Appendix A request per candidate, each checked (results/cell_requests/)
cell-requests:
	$(PY) src/write_cell_requests.py

# step 8, part 2: hd_reduced.lib plus the new cells (libs/hd_reduced_plus_new_cells_est.lib), checked with Yosys
liberty-with-new-cells: cell-requests
	$(PY) src/write_liberty_with_new_cells.py

# step 9: every design with and without the new cells, scripts A and B (results/mapping_areas.csv)
mapping: liberty-with-new-cells
	$(PY) src/map_with_and_without_new_cells.py

# step 9: every mapping checked against the RTL with ABC: cec, or dsec with flip-flops (results/mapping_equivalence.csv)
mapping-equivalence: mapping
	$(PY) src/check_mapping_equivalence.py

# Verilog models of the new cells, for simulation (libs/new_cell_verilog_sims.v)
new-cell-verilog-sims: cell-requests
	$(PY) src/write_new_cell_verilog_sims.py

# step 9: Tutorial 4's gate-level testbenches on SPM and mul. Runs on the host
# (Icarus Verilog 13; the pack image has none), after `make all` in the image.
gate-level-testbenches:
	$(PY) src/run_gate_level_testbenches.py

# section 7: Table 5 with estimated areas, best of both, total (results/table5_estimated.md)
table5-estimated: mapping-equivalence
	$(PY) src/write_table5.py --tag estimated

all: hd-classes selftest aigs stats table1 candidates cell-requests liberty-with-new-cells mapping mapping-equivalence new-cell-verilog-sims table5-estimated

IN  ?= tests/designs/csa8.v
TOP ?= csa8
demo:
	$(PY) src/demo.py $(IN) $(TOP)

clean:
	rm -rf build/aig build/demo build/smoke build/canon.npz src/__pycache__ tests/__pycache__

-include final.mk
