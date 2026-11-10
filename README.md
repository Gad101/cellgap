# Project 1, Option 2: Finding Cells Worth Adding

## 1. Group
Abdelrahman Rashed, 900231248 · Ziad Khairaldin, 900225292 · Option 2 · AI used as a development aid

## 2. Quick start
Tools used: Python 3.12 (3.11 or newer), numpy 1.26, native Yosys 0.33 (git sha1 2584903a060, Ubuntu 24.04 apt),
HD Liberty `sky130_fd_sc_hd__tt_025C_1v80.lib` from open_pdks `bdc9412b3e468c102d01b7cf6337be06ec6e9c9a`
(installed with `volare enable --pdk sky130 --include-libraries sky130_fd_sc_hd <version>`;
sha256 `e66aab4e0a3eef8d0b13eb5b75aaadb725ba78b032203342eb1e419a2c111baf`).

    make setup PACK=<unzipped student pack> PDK_ROOT=<your PDK_ROOT>   # < 1 minute
    make check                                                          # seconds
    make test                                                           # ~5 seconds
    make all                                                            # minutes (Table 1 maps 6 designs x 4)

`YOSYS=<command>` selects the Yosys binary (default `yosys`).

Table 1 needs native Yosys 0.33, the version in Ubuntu 24.04's apt (Homebrew's newer
builds and `yowasp-yosys` give different script A areas). We run the flow in the student
pack's course image (`container/Dockerfile`, Ubuntu 24.04) with `yosys python3-numpy` added
to its apt line, mounting the repo and pack at their real paths so the `build/` links resolve
(run from the repo root; `-w "$PWD"` is the directory `make` runs in):

    docker build -t dd2-layout-tools <pack>/container
    docker run --rm -v "$HOME/dd2:$HOME/dd2" -w "$PWD" dd2-layout-tools make all   # prints TABLE 1 REPRODUCED
    docker run --rm -v "$HOME/dd2:$HOME/dd2" -w "$PWD" dd2-layout-tools make final # greedy set, curve, final Table 5, 30%, ISA

**Interview demo** (any design, from a clean checkout after `make setup`; 5 s for csa8, 30 s for a 12k-AND design):

    docker run --rm -v "$HOME/dd2:$HOME/dd2" -w "$PWD" dd2-layout-tools make demo IN=<design.v or folder> TOP=<top module> [FLAGS=-sv]

If a real cell is wanted for the demo design itself (the demo already writes its Appendix A requests to
`build/demo/<top>/cell_requests/`), one command sends them to the generator (~30-45 min per cell, in the
tools image below):

    docker run --rm -v "$HOME/dd2:$HOME/dd2" -v "$HOME/cellweaver:$HOME/cellweaver" -e PDK_ROOT=$HOME/dd2/pdk-cw -w "$PWD" \
        dd2-layout-tools-sta python3 src/run_cellweaver.py --cellweaver $HOME/cellweaver --python /opt/cw/bin/python \
        --netgen /opt/netgen-cw/bin/netgen --magic /opt/magic-cw/bin/magic --jobs 7 \
        --requests-dir build/demo/<top>/cell_requests --only <cell name>

**Real cells and worst delay** (step 11, section 7) need OpenSTA and the course's cell generator
[cellweaver](https://github.com/shalan/cellweaver). `container/Dockerfile` adds both to the pack image
(OpenSTA built from source at a fixed commit; cellweaver's pinned Python packages). cellweaver also needs
the SKY130 device models (`sky130_fd_pr`), which our HD-only PDK lacks; we installed the same open_pdks
version with them in a separate root, so the PDK the flow uses is unchanged:

    git clone https://github.com/shalan/cellweaver $HOME/cellweaver
    docker build -t dd2-layout-tools-sta -f container/Dockerfile $HOME/cellweaver
    ciel enable --pdk-root $HOME/dd2/pdk-cw --pdk-family sky130 -l sky130_fd_sc_hd -l sky130_fd_pr bdc9412b3e468c102d01b7cf6337be06ec6e9c9a
    docker run --rm -v "$HOME/dd2:$HOME/dd2" -v "$HOME/cellweaver:$HOME/cellweaver" -e PDK_ROOT=$HOME/dd2/pdk-cw -w "$PWD" \
        dd2-layout-tools-sta make real-cells CELLWEAVER=$HOME/cellweaver JOBS=7     # ~30 min per cell
    docker run --rm -v "$HOME/dd2:$HOME/dd2" -w "$PWD" dd2-layout-tools-sta \
        bash -c "make real-lib && python3 src/final_table5.py && make curve-real"

`src/run_cellweaver.py` truncates each SPICE waveform once its point is measured (the values live in the
point's checkpoint), so the generator peaks well under 1 GB of disk per cell instead of ~10 GB;
`--keep-waveforms` keeps the evidence files.

## 3. What the tool does
It turns each synthesized design into an and-inverter graph (AIG), lists every
cut of up to 4 inputs with its truth table, groups the tables into classes, and
checks each class against every single-output combinational HD cell. Later steps
(checkpoint 2 and after) cost and rank the classes HD lacks, add them to a
Liberty file, and measure the area saving. Order of the steps:

1. `src/make_aig.sh`: design -> AIG (Yosys: synth, async2sync, dffunmap, aigmap, write_aiger -zinit;
   reproduces the handout's Table 2 AND counts exactly), and the same AIG after ABC's
   `strash; dch` (`src/abc_after.sh`; a final `strash` drops dch's choice nodes), checked with `cec`
2. `src/cuts.py`: cut enumeration, truth tables, and the cut check
3. `src/tt.py`: classes up to input order (P), input order and output inversion (PO), and NPN
4. `src/cmos.py`: transistors of one CMOS stage, at most 3 in series
5. `src/redundancy.py`: Exists / Exists with an inverter / Contained / New, and the self-test
6. `src/costmodel.py`: cost of each class (stages, inverters, transistors) and the area model fitted to HD's x1 cells
7. `src/candidates.py`: Table 3 applied, exclusive cones, estimated saving, ranking
8. `src/write_cell_requests.py`, `src/write_liberty_with_new_cells.py`: Appendix A requests and the Liberty file
9. `src/map_with_and_without_new_cells.py`, `src/check_mapping_equivalence.py`: mapping (scripts A and B) and cec/dsec against the RTL
10. `src/select_final_set.py`: greedy final set by remapping
11. `src/run_cellweaver.py`, `src/real_lib.py`: real cells from the course generator in place of the estimates
12. `src/sensitivity.py`: one final cell 30% smaller, remapped

`src/final_table5.py` writes the final Table 5 (with `src/worst_delay.py`, OpenSTA), `src/make_curve.py` the
cell-by-cell curve; `src/demo.py` runs steps 1 to 10 on one new design (`make demo`).

## 4. Commands
| Command | Input | Output |
|---|---|---|
| `make setup` | `PACK`, `PDK_ROOT` | links in `build/pdk/` and `build/given/` |
| `make check` | | tool versions (fails unless Yosys 0.33), Liberty hash, given files present |
| `make test` | `tests/` | every check and every broken case |
| `make selftest` | HD Liberty | `results/table4_selftest.txt` |
| `make hd-classes` | HD Liberty | `results/hd_class_table.{csv,md}` |
| `make aigs` | student-pack designs | `build/aig/<design>.aag`, and `<design>_abc.aig` after ABC `strash; dch` (checked with `cec`) |
| `make stats` | AIGs | `results/design_stats.csv` (before/after ABC), `results/cuts/<design>[_abc].json` |
| `make table1` | designs, `hd_usable.lib`, `hd_reduced.lib` | `results/table1.{csv,md}`, `results/logs/table1/` |
| `make cell-requests` | `results/candidates.json` | `results/cell_requests/<cell>.json`: one Appendix A request per candidate, each passing `request.py`'s check |
| `make liberty-with-new-cells` | `results/cell_requests/`, `hd_reduced.lib` | `libs/hd_reduced_plus_new_cells_est.lib`: the reduced library plus the new cells (section 6 format); checked: Yosys imports 189 + N cell types, each new cell's function matches its request |
| `make mapping` | the designs (6 required, SPM, mul), `hd_reduced.lib`, `libs/hd_reduced_plus_new_cells_est.lib` | `results/mapping_areas.csv`, `results/logs/mapping/`, `results/netlists/`: each design with and without the new cells, scripts A and B (section 2 commands); baseline must equal Table 1 |
| `make mapping-equivalence` | `results/netlists/` | `results/mapping_equivalence.csv`, `results/logs/mapping_equivalence/`: every mapping against the RTL (synth + dfflibmap) with ABC `cec`, or `dsec` when the design has flip-flops |
| `make new-cell-verilog-sims` | `results/cell_requests/` | `libs/new_cell_verilog_sims.v`: one Verilog model per new cell (its function), for simulation |
| `make gate-level-testbenches` (**on the host**, Icarus Verilog 13) | SPM and mul netlists, Tutorial 4 / 2 testbenches, PDK cell models | `results/gate_level_testbenches.csv`, `results/logs/gate_level_testbenches/`: SPM_tb, mul_tb, mul_exhaustive_tb with Tutorial 4's iverilog command |
| `make table5-estimated` | `results/mapping_areas.csv`, `results/mapping_equivalence.csv` | `results/table5_estimated.{md,csv}`: handout Table 5 with estimated areas, best of both per design, total over the required designs |
| `make all` | | all of the above |
| `make final-set` | `results/cell_requests/` | step 10, greedy: `results/greedy_log.csv` (every try), `results/final_set.json` (kept cells, total after each), `libs/hd_reduced_plus_final_set_est.lib` |
| `make curve` | `results/final_set.json` | `results/curve.{csv,md,svg}`: total best-of-both area after each final cell |
| `make real-cells CELLWEAVER=<clone>` (**tools image**, see Quick start) | `results/final_set.json` | step 11: each final cell built by the course's generator (cellweaver: DRC, LVS, abutment, extracted-RC characterization); `libs/real/<cell>.lib`, `results/real_cells/`, `cells/<cell>/` with the Appendix A response |
| `make real-lib` | `libs/real/` | `libs/hd_reduced_plus_final_set_real.lib` (estimated cells replaced by the real ones; Yosys imports 189 + N), `results/real_vs_estimated_area.csv` |
| `make final-table5` | final libraries, baseline mappings | `results/table5_final_{est,real}.{md,csv}`, `results/final/`, `results/netlists/final_{est,real}/`, `results/logs/final_*`; with OpenSTA (`sta`) on the PATH also `results/worst_delay.csv` (`src/worst_delay.py`) |
| `make sensitivity` | final set | step 12: `results/sensitivity_30pct.{md,csv}` (one final cell 30% smaller, remapped) |
| `make isa` | risc8, pic16, p16c5x | `results/isa_compare.{md,csv}`, `results/isa/`: do the three PIC16C5x designs favour the same cells? |
| `make final` | | `final-set curve final-table5 sensitivity isa` |
| `make demo IN=<design> TOP=<top> [FLAGS=-sv]` | a design: one `.v`/`.sv`, a folder, or `"a.v b.v"` | **the interview run**: steps 1 to 10 on that design alone (AIG before/after ABC, cut check, classes, redundancy, ranking, requests, Liberty, mapping with and without the new cells, equivalence, greedy set), then the design mapped with the project's final set (estimated and real); `build/demo/<top>/` with `table5_demo.md`; PASS/FAIL |
| `make clean` | | removes `build/` outputs |
| `python3 src/request.py check <req.json>` | a cell request | PASS or REFUSED |

## 5. Layout
- `src/`: the tool
- `container/`: the tools image for step 11 and OpenSTA (the pack image plus OpenSTA and cellweaver's packages)
- `tests/`: `test_all.py`; `designs/` (our own small test designs); `aig/` (their AIGs); `broken/` (broken cases)
- `results/`: every table and log the reports use
- `libs/`: the Liberty files the tool writes; `libs/real/` the generator's characterized cells
- `cells/`: one folder per real cell (overview Appendix A): cell.gds/.lef/.lib/.v/.mag/.spice, the generator's report.json, and response.json in the Appendix A response format
- `ai/`: AI use log and AI mistakes log
- `report/`: report.pdf and ai_report.pdf with sources

## 6. Results
### Checkpoint 1
- `results/table4_selftest.txt`: redundancy self-test. 258/258 HD cells -> Exists;
  Table 4 class rows 24 / 20 / 38 / 3,822 reproduced exactly; read-once rows 8 / 6 / 2
  and New one-stage 9 reproduced; New one-stage within 3-in-series and 12 T: **6, handout 5**
  (see Limitations).
- `results/hd_class_table.md`: 258 HD cells with <= 4 inputs in 29 PO classes, 13 NPN classes.
- `results/design_stats.csv`: AIG size, cuts and classes per design, before and after ABC's
  `strash; dch` (rows `before`, `after_abc`; needs the student pack). The `before` AND counts
  equal handout Table 2 (1,265 / 1,973 / 3,221 / 4,673 / 7,750 / 8,795). The `latches` column is
  Table 2's flip-flops plus one: the latch `-zinit` adds to mark the first cycle (82 -> 83 for cpu8). `after_abc` is checked
  equivalent to `before` with ABC's `cec` (`build/aig/<design>_abc.log`).
- `results/table1.md`: Table 1 reproduced exactly, all 24 areas (needs the student pack).

**Checkpoint 1 corrected after tag `cp1` (4 Nov 2026).** At `cp1`, Table 1 differed from the
handout (up to 6.6%, script A) and the AIGs had 3 fewer AND nodes per flip-flop than Table 2.
Fixes, all on `main` and in `cp2` (the `cp1` tag is not moved):
- Yosys: native 0.33 in the student pack's image instead of `yowasp-yosys` (mistake M-04);
  `make check` now requires 0.33. Table 1 is reproduced exactly.
- Step 1: `write_aiger -zinit` and no `opt_clean`, as in the handout; AND counts equal Table 2
  (mistake M-05). The after-ABC graph of step 1 was missing and is added (`src/abc_after.sh`).
- Every result was regenerated from the corrected checkpoint 1, including the checkpoint 2
  candidates: the ranking changed (top candidate 0xEEFA, 36.7 um2, was 0xAABF, 250.0 um2).

### Checkpoint 2 (Person B: write, map and measure)
- Every design the flow analyses, maps and ranks on: the 6 required designs plus SPM and mul
  (`ANALYSED` in `src/designs.py`); `design_stats.csv` and `candidate_stats.csv` have rows for all 8.
  SPM and mul add no estimated saving to any candidate, so the 11 cells are the same as with the
  6 required designs alone.
- `results/cell_requests/`: 11 Appendix A requests, one per candidate with estimated saving > 0,
  each passing `src/request.py`'s check.
- `libs/hd_reduced_plus_new_cells_est.lib`: hd_reduced.lib plus the 11 new cells (estimated areas,
  section 6 placeholders, timing_sense from the truth table); Yosys imports 200 = 189 + 11 cell types.
- `results/mapping_areas.csv`, `results/netlists/`, `results/logs/mapping/`: 8 designs (6 required,
  SPM, mul) x {baseline, with new cells} x {script A, B}; the baseline equals Table 1.
- `results/mapping_equivalence.csv`: 32 of 32 mappings equivalent to the RTL (ABC `dsec` for designs
  with flip-flops, `cec` for mul).
- `results/gate_level_testbenches.csv`: SPM_tb, mul_tb and mul_exhaustive_tb pass on all 8 SPM and
  mul netlists (12 of 12 runs; run on the host with Icarus Verilog 13).
- `results/table5_estimated.md`: Table 5 with estimated areas. Best of both over the required
  designs: 86,245.3 -> 86,157.7 um2, **0.10%** smaller; largest per design arlet6502 0.49%. With
  script B alone fir10 is 1.89% smaller, but 0.00% against the best of both, because script A
  without new cells is smaller still; SPM with script B is 1.33% larger.
### Checkpoint 3 (final set, real cells, delay, 30%, ISA)
- `results/final_set.json`, `results/greedy_log.csv`: step 10's greedy selection over the 11 ranked
  candidates, remapping the 6 required designs per try. Kept: `dd2_gb2__f17_1`, `dd2_gb2__f17ff_1`,
  `dd2_gb2__f07ff_1` (all three single-stage). Estimated total: 86,245.2 -> 86,102.6 um2 (**0.165%**).
- `results/table5_final_est.{md,csv}`: Table 5 with estimated areas, all 32 mappings cec/dsec pass,
  worst delay per design from OpenSTA (`results/worst_delay.csv`, `src/worst_delay.py`).
- `results/real_cells/`, `libs/real/`: the three cells built by the course generator (cellweaver, single
  height), each passing Magic DRC, Netgen LVS, abutment and extracted-RC characterization; OpenSTA
  validates each Liberty. Real areas are 2.0x / 3.0x / 2.17x the estimates
  (`results/real_vs_estimated_area.csv`).
- `results/table5_final_real.{md,csv}`: Table 5 with real areas. ABC almost never picks the real cells
  (fir10 B: 2 instances); best-of-both total 86,245.3 -> 86,239.0 um2 (**0.01%**): the estimated saving
  all but disappears with real areas (see the report's discussion).
- `results/curve.{csv,md,svg}` and `results/curve_real.*`: the cell-by-cell curve, estimated and real.
- `results/sensitivity_30pct.{md,csv}`: step 12, `dd2_gb2__f17_1` 30% smaller and remapped.
- `results/isa_compare.{md,csv}`: risc8 / pic16 / p16c5x candidate overlap.
- `results/gate_level_testbenches.csv`: 24 of 24 runs pass (baseline, est, final est, final real).

## 7. Tests
`make test` (63 tests; 2 skip in the image) runs `tests/test_all.py`, `tests/test_candidates.py`, `tests/test_abc_after.py`, `tests/test_liberty_with_new_cells.py`, `tests/test_mapping_equivalence.py`, `tests/test_gate_level_testbenches.py` (needs Icarus, so it runs on the host and skips in the image) and `tests/test_final_set.py`:
| Check | Broken case (in `tests/broken/`) |
|---|---|
| Truth tables: Appendix A example is 0x077F; 3,984 P and 222 NPN classes | |
| Request check: expression and truth table agree | `wrong_expression.json`: 0x077E must be refused |
| Cut check: every cut's table equals a per-combination simulation of the AIG | `wrong_cut_table.json`: one flipped row must be caught |
| Cut check: the leaves really cut the node off from the inputs | `not_a_cut.json`: a dropped leaf must be caught |
| Binary and ASCII AIGER give the same cuts | |
| Redundancy self-test: every HD cell -> Exists, Table 4 class rows | `hd_missing_cells.json`: without a22oi, Table 4 must not match |
| After-ABC AIG equals the original (`src/aig_equiv.sh`, ABC `cec`; `tests/test_abc_after.py`) | in the test file: csa8 with AND 40's first input inverted must be rejected |
| Timing sense (`src/timing_sense_calc.py`) agrees with HD's own `timing_sense` for every input of every single-output HD cell; nand2/and2/xor2 by hand (`tests/test_liberty_with_new_cells.py`) | |
| Liberty file loads in Yosys (`read_liberty -lib`) | in `tests/test_liberty_with_new_cells.py`: an unclosed quote must make Yosys reject it |
| Yosys imports 189 + N cell types | in `tests/test_liberty_with_new_cells.py`: a missing brace; Yosys 0.33 reads it without error but imports 190, so the count must fail |
| Each new cell's function equals its request's truth table | in `tests/test_liberty_with_new_cells.py`: a function using a pin the cell lacks must be reported |
| Every mapped netlist equals the RTL (`src/check_mapping_equivalence.py`: ABC `cec`, or `dsec` with flip-flops; `tests/test_mapping_equivalence.py`) | in `tests/test_mapping_equivalence.py`: one nand2_1 swapped for a nor2_1 in mul (cec) and in cpu8 (dsec) must be rejected |
| Cost formula computes its class (`costmodel.verify`, `tests/test_candidates.py`) | in `tests/test_candidates.py`: a formula for another function (0x0707 with `!(A & B)`) must be rejected |
| Greedy rule keeps a cell only if the best-of-both total drops by > 0.05 um2 (`tests/test_final_set.py`) | a cell that makes the total larger, and a gain below rounding, must both be dropped |
| Final Table 5: best of both, totals over the required designs, equivalence carried through (`tests/test_final_set.py`) | a failed equivalence must show as FAIL; a real Liberty file with a missing or unbalanced cell group must be refused |
| SPM and mul netlists (baseline, est, final est, final real) pass Tutorial 4's gate-level testbenches (`src/run_gate_level_testbenches.py`; `tests/test_gate_level_testbenches.py`, host only) | in `tests/test_gate_level_testbenches.py`: mul with one nand2_1 swapped for a nor2_1 must fail mul_exhaustive_tb |

## 8. AI use
AGENTS.md · ai/use_log.md · ai/mistakes_log.md · report/ai_report.pdf

## 9. Limitations
- Table 4, row "New, one stage, at most 3 transistors in series and at most 12 transistors":
  we count 6, the handout 5. The self-test prints a 12-transistor pull-down formula for
  each of our 6 classes with its series counts, checked by re-reading the formula. The
  6 form three dual pairs (0x0017/0x17FF, 0x011F/0x077F, 0x013F/0x037F: swap the pull-up and
  pull-down networks), so any rule that treats nMOS and pMOS alike gives an even count. Limiting
  only the nMOS stack, only the pMOS stack, or one of them to 4 still gives 6; algebraic
  factoring of the minimal SOP (no x&x = x) gives 4, losing 0x0017 and 0x013F, whose only
  12-transistor forms within 3 in series need Boolean factoring. No rule we tried gives 5.
  Question for the TA: which of the six does the reference reject, and by which test?
- Table 1 reproduces exactly (all 24 areas) only with native Yosys 0.33 (Ubuntu 24.04 apt, in the
  student pack's course image). `yowasp-yosys` 0.33 reports the same version but differs in script A by up to
  6.6% (fir10); native Yosys 0.70 also differs (cpu8 A 4169.0 vs 4186.5). The AIGs (and so the
  risc8 cut counts) also depend on the build; all results here come from that image.
- Cuts are fully enumerated (no limit per node); `--max-cuts` exists if a large design is slow.

## 10. Third-party files
- `sky130_fd_sc_hd__tt_025C_1v80.lib`: SkyWater SKY130 PDK, Apache 2.0, linked, not committed.
- Student-pack designs: their own licences (see each file), linked, not committed.
