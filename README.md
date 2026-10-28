# Project 1, Option 2: Finding Cells Worth Adding

## 1. Group
<name 1, student ID> · <name 2, student ID> · Option 2 · AI used as a development aid

## 2. Quick start
Tools used: Python 3.13 (3.11 or newer), numpy 2.x, Yosys 0.33 (git sha1 2584903a0),
HD Liberty `sky130_fd_sc_hd__tt_025C_1v80.lib` from open_pdks `bdc9412b3e468c102d01b7cf6337be06ec6e9c9a`
(installed with `volare enable --pdk sky130 --include-libraries sky130_fd_sc_hd <version>`;
sha256 `e66aab4e0a3eef8d0b13eb5b75aaadb725ba78b032203342eb1e419a2c111baf`).

    make setup PACK=<unzipped student pack> PDK_ROOT=<your PDK_ROOT>   # < 1 minute
    make check                                                          # seconds
    make test                                                           # ~5 seconds
    make all                                                            # minutes (Table 1 maps 6 designs x 4)

`YOSYS=<command>` selects the Yosys binary (default `yosys`).

## 3. What the tool does
It turns each synthesized design into an and-inverter graph (AIG), lists every
cut of up to 4 inputs with its truth table, groups the tables into classes, and
checks each class against every single-output combinational HD cell. Later steps
(checkpoint 2 and after) cost and rank the classes HD lacks, add them to a
Liberty file, and measure the area saving. Order of the steps:

1. `src/make_aig.sh`: design -> AIG (Yosys: synth, async2sync, dffunmap, aigmap, write_aiger)
2. `src/cuts.py`: cut enumeration, truth tables, and the cut check
3. `src/tt.py`: classes up to input order (P), input order and output inversion (PO), and NPN
4. `src/cmos.py`: transistors of one CMOS stage, at most 3 in series
5. `src/redundancy.py`: Exists / Exists with an inverter / Contained / New, and the self-test
6. to 12. checkpoint 2 and 3

## 4. Commands
| Command | Input | Output |
|---|---|---|
| `make setup` | `PACK`, `PDK_ROOT` | links in `build/pdk/` and `build/given/` |
| `make check` | | tool versions, Liberty hash, given files present |
| `make test` | `tests/` | every check and every broken case |
| `make selftest` | HD Liberty | `results/table4_selftest.txt` |
| `make hd-classes` | HD Liberty | `results/hd_class_table.{csv,md}` |
| `make aigs` | student-pack designs | `build/aig/<design>.aag` |
| `make stats` | AIGs | `results/design_stats.csv`, `results/cuts/<design>.json` |
| `make table1` | designs, `hd_usable.lib`, `hd_reduced.lib` | `results/table1.{csv,md}`, `results/logs/table1/` |
| `make all` | | all of the above |
| `make demo IN=<design.v> TOP=<top>` | a design | AIG, cut check, most frequent functions and their HD class |
| `make clean` | | removes `build/` outputs |
| `python3 src/request.py check <req.json>` | a cell request | PASS or REFUSED |

## 5. Layout
- `src/`: the tool
- `tests/`: `test_all.py`; `designs/` (our own small test designs); `aig/` (their AIGs); `broken/` (broken cases)
- `results/`: every table and log the reports use
- `libs/`: the Liberty files the tool writes (from checkpoint 2)
- `ai/`: AI use log and AI mistakes log
- `report/`: report.pdf and ai_report.pdf with sources

## 6. Results (checkpoint 1)
- `results/table4_selftest.txt`: redundancy self-test. 258/258 HD cells -> Exists;
  Table 4 class rows 24 / 20 / 38 / 3,822 reproduced exactly; read-once rows 8 / 6 / 2
  and New one-stage 9 reproduced; New one-stage within 3-in-series and 12 T: **6, handout 5**
  (see Limitations).
- `results/hd_class_table.md`: 258 HD cells with <= 4 inputs in 29 PO classes, 13 NPN classes.
- `results/design_stats.csv`: AIG size, cuts and classes per design (needs the student pack).
- `results/table1.md`: Table 1 reproduced (needs the student pack).

## 7. Tests
`make test` runs `tests/test_all.py`:
| Check | Broken case (in `tests/broken/`) |
|---|---|
| Truth tables: Appendix A example is 0x077F; 3,984 P and 222 NPN classes | |
| Request check: expression and truth table agree | `wrong_expression.json`: 0x077E must be refused |
| Cut check: every cut's table equals a per-combination simulation of the AIG | `wrong_cut_table.json`: one flipped row must be caught |
| Cut check: the leaves really cut the node off from the inputs | `not_a_cut.json`: a dropped leaf must be caught |
| Binary and ASCII AIGER give the same cuts | |
| Redundancy self-test: every HD cell -> Exists, Table 4 class rows | `hd_missing_cells.json`: without a22oi, Table 4 must not match |

## 8. AI use
AGENTS.md · ai/use_log.md · ai/mistakes_log.md · report/ai_report.pdf

## 9. Limitations
- Table 4, row "New, one stage, at most 3 transistors in series and at most 12 transistors":
  we count 6, the handout 5. The self-test prints a 12-transistor pull-down formula for
  each of our 6 classes with its series counts, checked by re-reading the formula. The
  6 form three dual pairs (swap the pull-up and pull-down networks), so an even count is
  expected. Question for the TA: which network does the reference reject?
- Table 1 with `yowasp-yosys` 0.33 (Yosys and ABC compiled to WebAssembly): script B matches
  the handout exactly for cpu8, dsp8, uart_apb and fir10, and within 0.2% for arlet6502 and risc8;
  script A differs by up to 6.6% (fir10). Native Yosys 0.70 also differs (cpu8 A 4169.0 vs 4186.5),
  so the handout's numbers need a native Yosys 0.33 build. Question for the TA: which Yosys/ABC build
  produced Table 1?
- Cuts are fully enumerated (no limit per node); `--max-cuts` exists if a large design is slow.

## 10. Third-party files
- `sky130_fd_sc_hd__tt_025C_1v80.lib`: SkyWater SKY130 PDK, Apache 2.0, linked, not committed.
- Student-pack designs: their own licences (see each file), linked, not committed.
