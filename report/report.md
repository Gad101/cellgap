# DD2 Project 1, Option 2: Finding Cells Worth Adding

**Group gb2** · Abdelrahman Rashed (900231248) · Ziad Khairaldin (900225292)
**Option 2** (three-student option, cells from the course's cell generator) · **AI used as a development aid** (overview 4.1)
Repository: `github.com/Gad101/cellgap`, tag `final`; code and results at commit `@@COMMIT@@`
CSCE 3304 Digital Design II, Fall 2026

Every number below comes from a file in `results/` that the flow wrote (overview 4.3, rule 2); the file is named next to each table.

## 1. Introduction

The sky130_fd_sc_hd (HD) library already has most small single-stage functions. The question of Option 2 is which small functions that real designs compute again and again HD lacks, and whether a cell for them makes the designs smaller when Yosys maps them. We built `cellgap`, a deterministic tool (no AI model runs when it runs) that

1. turns each design into an and-inverter graph (AIG), before and after ABC restructuring;
2. enumerates every cut of up to 4 inputs with its truth table, and checks each cut by simulation;
3. groups the truth tables into classes up to input order and output inversion (and NPN);
4. costs each class in CMOS stages, inverters and transistors (at most 3 in series per stage);
5. checks every class against all single-output combinational HD cells (Table 3 of the handout);
6. estimates the area of the classes HD lacks with a model fitted to HD's x1 cells;
7. ranks them by estimated saving;
8. writes an Appendix A request per candidate and a Liberty file (hd_reduced.lib plus the new cells);
9. maps every design with and without the new cells (scripts A and B) and checks every netlist against the RTL;
10. selects a final set greedily by remapping;
11. replaces the estimated cells with real ones from the course generator (cellweaver) and measures again;
12. repeats the mapping with one cell 30% smaller.

`make all` runs steps 1 to 9, `make final` steps 10 and 12 and the final tables, `make real-cells real-lib` step 11, and `make demo IN=<design> TOP=<top>` runs steps 1 to 10 on one new design (the interview run).

## 2. Method

**Step 1, AIG** (`src/make_aig.sh`). The handout's commands: `read_verilog; synth -flatten -top; async2sync; dffunmap; aigmap; write_aiger -zinit`. With `-zinit` (and no extra `opt_clean`) the AND counts equal handout Table 2 for all six required designs (`results/design_stats.csv`); without it they do not. The after-ABC graph is `strash; dch; strash` (`src/abc_after.sh`); the final `strash` removes dch's choice nodes, which `write_aiger` would otherwise write as ANDs that drive nothing. Each after-ABC graph is checked equal to the original with ABC `cec`.

**Step 2, cuts** (`src/cuts.py`). Our own bottom-up enumerator: the cuts of an AND node are the pairwise unions of its fanins' cuts with at most 4 leaves, plus the trivial cut; each cut carries a 16-bit truth table built by stretching the fanins' tables onto the merged leaves. No cut limit is applied (full enumeration). The check (`check_cuts`) recomputes every cut's table by simulating the AIG cone for all 16 leaf combinations, and also checks that the leaves really separate the root from the primary inputs.

**Step 3, classes** (`src/tt.py`). Truth tables follow overview Appendix A (input A is bit 0). Canonical forms are precomputed for all 65,536 tables: P (input order), PO (input order and output inversion) and NPN. CMOS cells are compared up to input order and output inversion, because an input inverter costs 2 transistors in CMOS while NPN treats it as free; NPN classes are reported for comparison.

**Step 4, cost** (`src/costmodel.py`, `src/cmos.py`). For each class the cheapest of: a single static CMOS stage (pull-down from a factored form of !Y, pull-up its dual, at most 3 transistors in series in either network), the same with inverters on inputs or output, or a Shannon split into stages. Every cost carries a formula; `costmodel.verify` simulates the formula and must reproduce the class's truth table (3,984 of 3,984 classes).

**Step 5, redundancy** (`src/redundancy.py`). Each candidate is compared with every single-output combinational cell of the full HD Liberty (all drives and kinds, using the `function` attribute): Exists (same table after reordering inputs), Exists with an inverter (after inverting the output or one input), Contained (an HD cell with each input tied to a candidate input or a constant), else New. Following Table 3, Exists is dropped; Exists-with-an-inverter is kept only if its estimated area is below the HD cell plus `inv_1`; Contained only if below the HD cell.

**Step 6, area model** (`src/costmodel.py fit`). Width in 0.46 um sites against transistor count, two straight lines fitted to HD's x1 cells: one for single-stage cells (13 cells) and one for multi-stage cells (45 cells); `nand4_1` and `nor4_1` are left out (4 in series, outside our rule). Area = sites x 1.2512 um2 (2.72 um x 0.46 um), rounded up to whole sites.

**Step 7, ranking** (`src/candidates.py`). For each occurrence of a candidate in a design, the *exclusive cone* is the set of AND nodes that would disappear if that cut became one cell (nodes of the cone used only inside it). Estimated saving of an occurrence = m x a_AND - area(new cell), where a_AND is the combinational area per AND node of that design's baseline mapping (best of A and B, from the Table 1 logs) and m is the exclusive-cone size capped at the smallest cone seen for that function (the Yosys AIG is not optimized and ABC would not pay for redundant structure). Per design, non-overlapping occurrences with positive saving are picked greedily, and classes are ranked by the total. This is a guess (handout step 7); steps 9 and 10 measure.

**Step 8, requests and Liberty** (`src/write_cell_requests.py`, `src/write_liberty_with_new_cells.py`). One Appendix A request per ranked candidate, refused unless its expression and truth table agree (`src/request.py`). The Liberty file is hd_reduced.lib with the new cells inside the same library group, each with area, input capacitance, function and one timing arc per input (placeholder scalar values as in handout section 6; `timing_sense` derived from the truth table and checked against HD's own on every HD pin). Yosys must import 189 + N cell types, and every new cell's function must give its request's truth table.

**Step 9, mapping and equivalence** (`src/map_with_and_without_new_cells.py`, `src/check_mapping_equivalence.py`). The exact commands of handout section 2 (through `table1.map_design`, the same code that reproduces Table 1), with scripts A and B, only the library changing. A `write_verilog` after `stat` saves each netlist. Each netlist is flattened with the Liberty functions into an AIG and compared with the RTL taken through `synth -flatten; dfflibmap` (same flip-flop cells): ABC `cec` without flip-flops, `dsec` with them (cec pairs flip-flops by order, which differs between the two sides). SPM and mul also run Tutorial 4's gate-level testbenches on the host with Icarus Verilog.

**Step 10, greedy final set** (`src/select_final_set.py`). In rank order: add the next candidate to the cells kept so far, remap the six required designs with A and B, keep it only if the total best-of-both area drops by more than 0.05 um2 (Yosys prints areas to 0.1 um2), stop after 10 kept cells or at the end of the list. Each candidate is tried once.

**Step 11, real cells** (`src/run_cellweaver.py`, `src/real_lib.py`). Each final request is sent to the course generator cellweaver (`--verify --characterize`: Magic DRC, Netgen LVS, extracted-RC characterization with ngspice, Liberty checked with OpenSTA), at single (2.72 um) height. The characterized TT Liberty cell replaces the estimated entry one for one; Yosys must again import 189 + N and every function must match its request.

**Step 12, sensitivity** (`src/sensitivity.py`). The final cell used most often is made 30% smaller in the Liberty, everything else equal, and all designs are remapped.

**Delay** (`src/worst_delay.py`). OpenSTA times every baseline and final netlist with the same constraints: a 10 ns clock on the port that drives the flip-flops (a virtual clock for mul), all other inputs and outputs at 0 ns, no wire load. The worst delay is the data arrival time of the path with the least slack.

**Choices.** Full cut enumeration (no priority cuts), so frequencies are exact for the AIG Yosys writes; classes up to input order and output inversion for CMOS; the baseline is hd_reduced.lib in every comparison; the best of scripts A and B is the number conclusions rest on.

## 3. Verification

`make test` runs 63 tests (61 in the pack image; the two Icarus testbench tests run on the host). Every check has a broken case that must fail (overview 4.3, rule 3):

| Check | Broken case that must fail |
|---|---|
| Request: expression and truth table agree | `tests/broken/wrong_expression.json` (0x077E for the 0x077F formula) is refused |
| Cut check: table equals simulation | `tests/broken/wrong_cut_table.json` (one flipped row) is caught |
| Cut check: leaves separate root from inputs | `tests/broken/not_a_cut.json` (a dropped leaf) is caught |
| Redundancy self-test: every HD cell Exists; Table 4 rows | `tests/broken/hd_missing_cells.json` (HD without a22oi) no longer reproduces Table 4 |
| Cost formula computes its class | a formula for another function (0x0707 with !(A&B)) is rejected |
| After-ABC AIG equals the original (ABC cec) | csa8 with one AND input inverted is rejected |
| Liberty loads in Yosys | an unclosed quote is rejected |
| Yosys imports 189 + N | a missing brace: Yosys 0.33 reads it without error but imports 190, so the count fails |
| New cell function equals its request | a function using a pin the cell lacks is reported |
| Mapped netlist equals the RTL (cec / dsec) | one nand2_1 swapped for nor2_1 in mul (cec) and cpu8 (dsec) is rejected |
| Gate-level testbenches (SPM, mul) | mul with one nand2_1 swapped for nor2_1 fails mul_exhaustive_tb |
| Greedy rule | a cell that makes the total larger, and a gain below rounding, are both dropped |
| Final table | a failed equivalence is marked FAIL; a real Liberty file with a missing or unbalanced cell group is refused |

**Calibration.** Table 1 is reproduced exactly, all 24 areas (`results/table1.md`, 0.000% on every row), with native Yosys 0.33 in the student pack's image. The AIG AND counts equal Table 2. The redundancy checker classifies 258 of 258 HD cells with at most 4 inputs as Exists and reproduces Table 4 (`results/table4_selftest.txt`): 24 Exists, 20 Exists with an inverter, 38 Contained, 3,822 New, 9 New one-stage, 8 read-once one-stage of which 6 Exist and 2 are Contained. One row differs: "New, one stage, at most 3 in series and at most 12 transistors", 6 against the handout's 5 (Section 7).

## 4. Results

### 4.1 Designs, cuts and classes (`results/design_stats.csv`)

| Design | ANDs before / after ABC | Cuts before / after | Classes (input order + output inversion) before / after | NPN before / after |
|---|---|---|---|---|
| cpu8 | 1,265 / 1,109 | 10,725 / 9,007 | 195 / 192 | 63 / 59 |
| dsp8 | 1,973 / 1,532 | 16,445 / 13,032 | 200 / 194 | 54 / 50 |
| arlet6502 | 3,221 / 2,699 | 27,091 / 20,438 | 205 / 207 | 51 / 60 |
| uart_apb | 4,673 / 2,971 | 39,290 / 17,934 | 203 / 134 | 45 / 38 |
| risc8 | 7,750 / 6,592 | 57,178 / 44,144 | 173 / 174 | 45 / 47 |
| fir10 | 8,795 / 6,937 | 92,196 / 75,435 | 176 / 171 | 43 / 43 |
| spm | 953 / 540 | 10,563 / 3,179 | 73 / 49 | 29 / 22 |
| mul | 774 / 512 | 8,221 / 5,356 | 192 / 159 | 52 / 36 |

The cut check passes on all 16 graphs. HD's class table (`results/hd_class_table.md`): 258 cells with at most 4 inputs fall into 29 classes up to input order and output inversion, and 13 NPN classes.

### 4.2 Redundancy (`results/redundancy_report.csv`)

Over the eight designs, 556 classes (up to input order) occur in real cuts. Table 3 removes 53 as Exists, 5 of 28 Exists-with-an-inverter (the other 23 are estimated smaller than the HD cell plus an inverter) and 2 of 30 Contained; 445 are New. Examples: 0x000F (!C & !D) Exists as nor2; 0x00EE Exists as o21ba; 0x07FF, !(D & (C | A&B)), is Contained in a32oi (estimated 7.51 um2 against a32oi_1's 8.76 um2, so it is kept); 0xEEFA is Contained in mux4 (12.51 against 22.52, kept).

### 4.3 Area model (`results/area_model.json`, `results/area_model_fit.csv`)

| Fit | Cells | Sites = a + b x transistors (rounded up) | Mean error | Max error | Worst cell |
|---|---|---|---|---|---|
| One stage | 13 | 1.053 + 0.553 T | 0.62 sites (15.9%) | 1 site | a21oi_1 |
| Multi-stage | 45 | 2.512 + 0.461 T | 0.98 sites (14.9%) | 3 sites | or4_1 |

### 4.4 Ranked candidates and final set (`results/candidates.json`, `results/greedy_log.csv`, `results/final_set.json`)

Eleven candidates have a positive estimated saving. The greedy step remaps all six required designs once per candidate:

| Try | Cell | Function | T / stages | Est. area | Est. saving | Total before -> after (um2) | Decision |
|---|---|---|---|---|---|---|---|
| 1 | feefa | !(!A & !(D&B | !D&C)) | 16 / 3 | 12.51 | 36.74 | 86,245.2 -> 86,282.8 | drop |
| 2 | f8ae6 | (4 stages) | 34 / 4 | 23.77 | 25.92 | 86,245.2 -> 86,245.2 | drop |
| 3 | **f17** | !(A&B | C&(A|B)) (inverted 3-input majority) | 10 / 1 | 8.76 | 12.01 | 86,245.2 -> 86,235.2 | **keep** |
| 4 | f077f | !((C|D) & (A&B | C&D)) (handout's maj4n) | 12 / 1 | 10.01 | 8.25 | 86,235.2 -> 86,235.2 | drop |
| 5 | **f17ff** | !(D & (A&B | C&(A|B))) | 12 / 1 | 10.01 | 5.50 | 86,235.2 -> 86,234.0 | **keep** |
| 6 | fbcc4 | (4 stages) | 34 / 4 | 23.77 | 3.70 | 86,234.0 -> 86,234.0 | drop |
| 7 | **f07ff** | !(D & (C | A&B)) | 8 / 1 | 7.51 | 2.84 | 86,234.0 -> 86,102.6 | **keep** |
| 8 | faabf | !(!A & (D | B&C)) | 10 / 2 | 10.01 | 1.59 | 86,102.6 -> 86,106.3 | drop |
| 9 | f0bbf | | 14 / 2 | 11.26 | 1.50 | 86,102.6 -> 86,102.6 | drop |
| 10 | f2bff | | 14 / 2 | 11.26 | 1.50 | 86,102.6 -> 86,102.6 | drop |
| 11 | f0eef | | 16 / 2 | 12.51 | 0.74 | 86,102.6 -> 86,102.6 | drop |

The final set is three single-stage cells: `dd2_gb2__f17_1`, `dd2_gb2__f17ff_1`, `dd2_gb2__f07ff_1`.

### 4.5 Table 5 with estimated areas (`results/table5_final_est.md`)

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence | Worst delay base / new (ns) |
|---|---|---|---|---|---|---|---|
| cpu8 | A | 4186.5 | 4186.5 | 0.00% | 1 | pass | 4.1754 / 4.2003 |
| cpu8 | B | 4359.2 | 4282.9 | 1.75% | 5 | pass | 4.1108 / 4.2375 |
| dsp8 | A | 5928.2 | 5914.4 | 0.23% | 10 | pass | 5.2175 / 5.2303 |
| dsp8 | B | 6214.7 | 6169.7 | 0.72% | 60 | pass | 5.6287 / 4.7001 |
| arlet6502 | A | 9701.8 | 9654.3 | 0.49% | 3 | pass | 7.1104 / 7.1355 |
| arlet6502 | B | 9995.8 | 9884.5 | 1.11% | 22 | pass | 8.6488 / 6.8682 |
| uart_apb | A | 12948.7 | 12939.9 | 0.07% | 0 | pass | 6.7771 / 6.7771 |
| uart_apb | B | 13180.1 | 13170.1 | 0.08% | 4 | pass | 4.4893 / 4.4893 |
| risc8 | A | 28263.4 | 28252.1 | 0.04% | 3 | pass | 15.9846 / 15.1987 |
| risc8 | B | 27511.4 | 27438.8 | 0.26% | 26 | pass | 13.3222 / 10.9840 |
| fir10 | A | 25968.7 | 25968.7 | 0.00% | 0 | pass | 6.2563 / 6.2563 |
| fir10 | B | 29055.4 | 28446.0 | 2.10% | 241 | pass | 6.2349 / 6.0064 |
| spm | A | 2869.0 | 2869.0 | 0.00% | 0 | pass | 0.7430 / 0.7430 |
| spm | B | 2907.8 | 2907.8 | 0.00% | 0 | pass | 0.6585 / 0.6585 |
| mul | A | 1756.7 | 1756.7 | 0.00% | 0 | pass | 4.2691 / 4.2691 |
| mul | B | 1948.1 | 1920.6 | 1.41% | 16 | pass | 4.7852 / 4.5741 |

Best of both (the smaller of scripts A and B on each side):

| Design | Baseline (um2) | With new cells (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4186.5 | 4186.5 | 0.00% |
| dsp8 | 5928.2 | 5914.4 | 0.23% |
| arlet6502 | 9701.8 | 9654.3 | 0.49% |
| uart_apb | 12948.7 | 12939.9 | 0.07% |
| risc8 | 27511.4 | 27438.8 | 0.26% |
| fir10 | 25968.7 | 25968.7 | 0.00% |
| spm | 2869.0 | 2869.0 | 0.00% |
| mul | 1756.7 | 1756.7 | 0.00% |
| **Total, required designs** | **86245.3** | **86102.6** | **0.17%** |

Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; with new cells: libs/hd_reduced_plus_final_set_est.lib. Equivalence: ABC cec against the RTL (dsec with flip-flops), results/final/mapping_equivalence_final.csv.

### 4.6 Table 5 with real cells (`results/table5_final_real.md`, `results/real_vs_estimated_area.csv`)

The generator (cellweaver, single height) built all three cells, passing Magic DRC, Netgen LVS, four-orientation
abutment and extracted-RC characterization; OpenSTA validated each Liberty (`results/real_cells/`). Their real
areas are 2 to 3 times the model's estimates (`results/real_vs_estimated_area.csv`): f17 8.76 -> 17.52 um2 (2.0x),
f17ff 10.01 -> 30.03 um2 (3.0x), f07ff 7.51 -> 16.27 um2 (2.17x). At these areas ABC almost never picks them:
fir10 script B uses 2 instances, everything else none, and the per-design changes are library-change noise.

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence | Worst delay base / new (ns) |
|---|---|---|---|---|---|---|---|
| cpu8 | A | 4186.5 | 4186.5 | 0.00% | 0 | pass | 4.1754 / 4.1754 |
| cpu8 | B | 4359.2 | 4279.1 | 1.84% | 0 | pass | 4.1108 / 4.2652 |
| dsp8 | A | 5928.2 | 5928.2 | 0.00% | 0 | pass | 5.2175 / 5.2175 |
| dsp8 | B | 6214.7 | 6216.0 | -0.02% | 0 | pass | 5.6287 / 5.4544 |
| arlet6502 | A | 9701.8 | 9701.8 | 0.00% | 0 | pass | 7.1104 / 7.1104 |
| arlet6502 | B | 9995.8 | 9930.8 | 0.65% | 0 | pass | 8.6488 / 6.2703 |
| uart_apb | A | 12948.7 | 12948.7 | 0.00% | 0 | pass | 6.7771 / 6.7771 |
| uart_apb | B | 13180.1 | 13183.9 | -0.03% | 0 | pass | 4.4893 / 4.4893 |
| risc8 | A | 28263.4 | 28263.4 | 0.00% | 0 | pass | 15.9846 / 15.9846 |
| risc8 | B | 27511.4 | 27505.1 | 0.02% | 0 | pass | 13.3222 / 13.5038 |
| fir10 | A | 25968.7 | 25968.7 | 0.00% | 0 | pass | 6.2563 / 6.2563 |
| fir10 | B | 29055.4 | 29044.1 | 0.04% | 2 | pass | 6.2349 / 6.3212 |
| spm | A | 2869.0 | 2869.0 | 0.00% | 0 | pass | 0.7430 / 0.7430 |
| spm | B | 2907.8 | 2907.8 | 0.00% | 0 | pass | 0.6585 / 0.6585 |
| mul | A | 1756.7 | 1756.7 | 0.00% | 0 | pass | 4.2691 / 4.2691 |
| mul | B | 1948.1 | 1988.2 | -2.06% | 0 | pass | 4.7852 / 5.0705 |

Best of both (the smaller of scripts A and B on each side):

| Design | Baseline (um2) | With new cells (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4186.5 | 4186.5 | 0.00% |
| dsp8 | 5928.2 | 5928.2 | 0.00% |
| arlet6502 | 9701.8 | 9701.8 | 0.00% |
| uart_apb | 12948.7 | 12948.7 | 0.00% |
| risc8 | 27511.4 | 27505.1 | 0.02% |
| fir10 | 25968.7 | 25968.7 | 0.00% |
| spm | 2869.0 | 2869.0 | 0.00% |
| mul | 1756.7 | 1756.7 | 0.00% |
| **Total, required designs** | **86245.3** | **86239.0** | **0.01%** |

Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; with new cells: libs/hd_reduced_plus_final_set_real.lib. Equivalence: ABC cec against the RTL (dsec with flip-flops), results/final/mapping_equivalence_final.csv.

### 4.7 Cell-by-cell curve (`results/curve.md`, `results/curve.svg`)

| Cells added | Cell | Total best-of-both area (um2) | Gain (um2) | Reduction |
|---|---|---|---|---|
| 0 | - | 86,245.2 | - | 0.000% |
| 1 | dd2_gb2__f17_1 | 86,235.2 | 10.0 | 0.012% |
| 2 | dd2_gb2__f17ff_1 | 86,234.0 | 1.2 | 0.013% |
| 3 | dd2_gb2__f07ff_1 | 86,102.6 | 131.4 | 0.165% |

With real cells the same curve is flat (`results/curve_real.md`): 86,245.2 -> 86,246.5 -> 86,244.0 -> 86,239.0 um2,
a final reduction of 0.007% against 0.165% estimated. The first cell alone makes the total 1.3 um2 larger.

### 4.8 The 30% experiment (`results/sensitivity_30pct.md`)

`dd2_gb2__f17_1`, the final cell used most, made 30% smaller (8.758 -> 6.131 um2). Script B uses it much more (fir10: 237 -> 403 instances, 1,187.7 um2 smaller; dsp8: 27 -> 40, 102.6 um2 smaller), script A never. Against the best of both the total of the required designs moves only from 86,102.6 to 86,100.7 um2 (-1.9 um2), because on fir10 script A without new cells (25,968.7) is still smaller than script B with the cheaper cell (27,258.3). The result depends strongly on the area estimate for script B, and hardly at all for the best of both.

## 5. Discussion

**Classes** (`results/class_counts.csv`). Over the eight designs, the cuts of the AIGs Yosys writes fall into 362 classes up to input order and output inversion, 326 of them using all 4 inputs; NPN gives 91 (78 with 4 inputs). After ABC's `strash; dch` the counts are 316 (285) and 86 (75). For CMOS the count up to input order and output inversion is the one that matters: swapping inputs is free (rewiring) and so is an inverted output (a stage inverts anyway, and the dual network gives the complement), but an inverted input costs an inverter, 2 transistors and usually a site, so NPN merges functions whose cells differ in cost. NPN's lower counts (Section 4.1) overstate how much one cell can cover.

**Why the saving differs between designs.** The new cells pay where script B's `&nf` maps many carry-like or and-or-invert cones: cpu8 B 1.75%, fir10 B 2.10% (241 instances), arlet6502 B 1.11%, mul B 1.41% with estimated areas. Script A (`amap`, structural matching) almost never uses them: it never used a cell with an input appearing twice (f17 and f17ff), as the handout warns, and used f07ff only in cpu8 (once), dsp8, arlet6502 and risc8. Against the best of both only dsp8 (0.23%), arlet6502 (0.49%), uart_apb (0.07%) and risc8 (0.26%) gain; on cpu8, fir10, spm and mul script A without new cells is already smaller than script B with them, so the best-of-both saving is zero. Total over the required designs: 0.17% (86,245.3 -> 86,102.6 um2).

**risc8, pic16 and p16c5x** (`results/isa_compare.md`) implement one instruction set but favour different cells: ranked on its own, risc8 has 6 candidates with positive estimated saving, pic16 none and p16c5x one (0x07FF, our third final cell, also rank 4 for risc8). Their most frequent New classes overlap more (pic16 and p16c5x share 9 of their top 10, Jaccard 0.82; risc8 shares 4 with each): the same ISA gives similar logic, but the synthesized structure, not the ISA, decides which cuts exist and which save area.

**Frequency against saving.** The handout's own example cell 0x077F (maj4n, the carry of a carry-save adder) occurs in SPM, and script B used it 31 times there, yet SPM with script B grew from 2,907.8 to 2,946.6 um2 (+1.33%, `results/table5_estimated.md`), and in the greedy step it saved nothing on the required designs (try 4: 0.0 um2). `&nf` chooses cuts by its own area-flow estimate in a relaxed-delay mode; replacing a carry by one 10.0 um2 cell removes the shared maj3/xor structure the full design reused, so the neighbouring logic is mapped with more cells. Likewise 0xEEFA was ranked first by estimate (36.7 um2, 216 cuts) and is used 24 times, but makes the total 37.5 um2 larger. Frequency of a cut says nothing about whether the logic around it gets cheaper.

**Delay** (`results/worst_delay.csv`, OpenSTA, Section 2 constraints). With estimated cells the new cells never make a design much slower: the largest increase is cpu8 B, 4.11 -> 4.24 ns (+3%), and with script B several designs get faster (risc8 13.32 -> 10.98 ns, arlet6502 8.65 -> 6.87 ns, dsp8 5.63 -> 4.70 ns), because one complex gate replaces a chain of two or three HD gates. These delays rest on placeholder timing (0.10 / 0.08 ns per arc, handout section 6), so they show only where the new cells sit on critical paths, not how fast they are. With real cells the mapped netlists barely change (ABC rarely uses them), so the worst delays track the baseline;
where script B does change, the real-timing arcs are measured, not placeholders (arlet6502 B 8.65 -> 6.27 ns).

## 6. Limitations

- **Table 4, one row.** "New, one stage, at most 3 in series and at most 12 transistors": 6 against 5. Each of our six has an explicit 12-transistor network within 3 in series, checked from its formula (`results/table4_selftest.txt`). They form three dual pairs (0x0017/0x17FF, 0x011F/0x077F, 0x013F/0x037F), so any rule that treats the two networks alike gives an even count; no rule we tried gives 5.
- **Area model.** Straight lines in transistor count; the real width depends on diffusion breaks, routing and pin access. Mean error about 15% (0.6 to 1 site), worst 3 sites. The real cells came back 2.0x, 3.0x and 2.17x the estimate: the model is fitted to HD's hand-packed x1 layouts,
while the generator's shared-diffusion cells spend sites on routing access and well taps that HD cells do not.
- **Cost model.** An upper bound: no inverter sharing between stages, no search over every factoring.
- **Ranking.** A guess: AND nodes times area per AND node, capped by the smallest cone. The structure of the Yosys AIG decides which cuts exist (reference 12); a function that appears after ABC restructuring may not be a cut of the graph we enumerate.
- **Greedy.** Each candidate is tried once in rank order; a candidate dropped early is not retried after later cells are kept.
- **Liberty.** Estimated cells have one scalar timing value per arc and a fixed input capacitance: both scripts aim at area, but the delays of estimated cells are placeholders. Real cells carry cellweaver's characterized TT tables only; no FF/SS corner, no power in the mapping.
- **Scripts.** Script A (`amap`) matches structure and does not use cells with a repeated input; script B (`&nf -R 1000`) relaxes delay. Neither optimizes delay, and both are heuristic: a library change alone moves script A by about 1% even when no new cell is used.
- **Tool versions.** Table 1 reproduces only with native Yosys 0.33 (Ubuntu 24.04 apt); `yowasp-yosys` 0.33 and Yosys 0.70 give different areas.

## 7. Contributions

| Member | Work |
|---|---|
| Abdelrahman Rashed (Person B) | AGENTS.md; truth tables, classes, Liberty reader, AIGER reader, cut enumerator and checks, redundancy checker and Table 4 self-test, Table 1 runner (checkpoint 1); cell requests, Liberty writer, mapping, equivalence, gate-level testbenches, Table 5 (checkpoint 2); the interview demo, OpenSTA delays, real cells, README and reports (checkpoint 3) |
| Ziad Khairaldin (Person A) | Cost model and area model, candidate finder and ranking (checkpoint 2); greedy final set, curve, final Table 5, 30% experiment, ISA comparison, real-cell hook (checkpoint 3) |

Both members agree with this table.

## Appendix: tool versions

| Tool | Version |
|---|---|
| Yosys (with yosys-abc) | 0.33 (git sha1 2584903a060), Ubuntu 24.04 apt, in the student pack image `dd2-layout-tools` |
| Python / numpy | 3.12.3 / 1.26.4 |
| HD Liberty | `sky130_fd_sc_hd__tt_025C_1v80.lib`, open_pdks `bdc9412b3e468c102d01b7cf6337be06ec6e9c9a`, sha256 `e66aab4e...2c111baf` |
| Icarus Verilog | 13 (host, Homebrew) |
| Magic / Netgen / ngspice | 8.3.684 / 1.5.133 / 47 with the BSIM4 stress fix (student pack image) |
| OpenSTA | 3.1.0, built from source at commit `f8e13cb` (container/Dockerfile) |
| cellweaver | github.com/shalan/cellweaver at `e7fd28e` (2026-10-15), with its qualified Magic 8.3.684 (`4f53bb3`) and Netgen 1.5.323 (`e1528a7`) built in container/Dockerfile |
