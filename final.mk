# Checkpoint 3 targets. Included from the Makefile by `-include final.mk`.
# Run in the pack image (Yosys 0.33) after `make all`, which writes the files these read.
#
#   make final          greedy set, curve, final Table 5, 30% test, ISA comparison
#   make real-cells CELLWEAVER=<clone>   then   make real-lib, make final-table5, make curve-real   (the "real" half)

JOBS ?= 2
export JOBS
ISA_DESIGNS := risc8 pic16 p16c5x

.PHONY: real-cells final final-set curve curve-real final-table5 sensitivity isa real-lib test-final

# step 10: greedy selection -> results/final_set.json, results/greedy_log.csv
final-set: cell-requests
	$(PY) src/select_final_set.py --jobs $(JOBS)

# section 7: total area after each final cell (results/curve.{csv,md,svg});
# curve-real remaps with the generator's real cells in the same order (results/curve_real.*)
curve: final-set
	$(PY) src/make_curve.py
curve-real:
	$(PY) src/make_curve.py --real --jobs $(JOBS)

# section 7: final Table 5 (needs `make mapping-equivalence` for the baseline rows)
final-table5: final-set mapping-equivalence
	$(PY) src/final_table5.py --jobs $(JOBS)

# step 12: one final cell 30% smaller, remap
sensitivity: final-table5
	$(PY) src/sensitivity.py --jobs $(JOBS)

# section 9.3: do risc8, pic16 and p16c5x favour the same cells? Each design is ranked on its own.
isa:
	@for d in pic16 p16c5x; do \
	  top=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import DESIGNS, files; print(DESIGNS['$$d'][0])"); \
	  fl=$$($(PY) -c "import sys; sys.path.insert(0,'src'); from designs import files; print(' '.join(files('$$d')))"); \
	  src/make_aig.sh "$$fl" $$top build/aig/$$d.aag || exit 1; done
	$(PY) src/map_with_and_without_new_cells.py --designs pic16,p16c5x --baseline-only
	@for d in $(ISA_DESIGNS); do \
	  $(PY) src/candidates.py --group $(GROUP) --designs $$d --out results/isa/$$d || exit 1; done
	$(PY) src/isa_compare.py

# step 11: real cells from the generator in place of the estimates
CELLS ?= libs/real
CELLWEAVER ?= $(HOME)/cellweaver
export CELLWEAVER
# cellweaver was qualified with its own Magic/Netgen commits and Python env; in the tools image
# (container/Dockerfile) they are at these paths, elsewhere the PATH tools are used.
CW_PY     ?= $(shell test -x /opt/cw/bin/python && echo /opt/cw/bin/python || echo $(CELLWEAVER)/.venv/bin/python)
CW_NETGEN ?= $(shell test -x /opt/netgen-cw/bin/netgen && echo /opt/netgen-cw/bin/netgen || echo netgen)
CW_MAGIC  ?= $(shell test -x /opt/magic-cw/bin/magic && echo /opt/magic-cw/bin/magic || echo magic)
# step 11a: generate the final-set cells with cellweaver (needs Magic, Netgen, ngspice, OpenSTA `sta`, the PDK
# with the sky130_fd_pr device models). The runner holds each state 30 ns (--settle), truncates each
# waveform once its point is measured, and stops cleanly if the disk runs low: peak disk < 2 GB per cell.
real-cells: final-set
	$(PY) src/run_cellweaver.py --cellweaver $(CELLWEAVER) --python $(CW_PY) \
	    --netgen $(CW_NETGEN) --magic $(CW_MAGIC) --jobs $(JOBS)

# step 11b: put their Liberty cells into a copy of the library
real-lib:
	$(PY) src/real_lib.py --cells $(CELLS)

test-final:
	$(PY) -m unittest -v tests/test_final_set.py

final: final-set curve final-table5 sensitivity isa
