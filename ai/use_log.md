# AI use log (overview, Appendix B, Table 5)

Tool and model for every row: Claude, model `claude-opus-5-5`, in the Claude app.
Fill in **Who** and **Commit** when you commit. Add a row for every new request.

| ID | Date | Who | Tool and model | What you asked | What you kept or changed | How you checked it | Commit |
|---|---|---|---|---|---|---|---|
| L-001 | 27 Oct 2026 | | Claude / claude-opus-5-5 | Write AGENTS.md before any code: how the project is checked, what the assistant must not do | Kept | Read it against overview 4.1 and 4.3 | |
| L-002 | 27 Oct 2026 | | Claude / claude-opus-5-5 | 16-bit truth tables and class tables (P, PO, NPN) for every 4-input function (`src/tt.py`), and an expression parser (`src/boolexpr.py`) | Kept | Appendix A example gives 0x077F; 3,984 P classes and 222 NPN classes, the textbook counts (`make test`) | |
| L-003 | 27 Oct 2026 | | Claude / claude-opus-5-5 | A Liberty reader for cell names, areas, pins and functions (`src/liberty.py`) | Kept | Reads 428 cells, the number the handout gives for the full HD library | |
| L-004 | 27 Oct 2026 | | Claude / claude-opus-5-5 | The redundancy checker of section 5 and its self-test against Table 4 (`src/redundancy.py`, `src/cmos.py`) | Kept; added a printout of one formula per one-stage class, re-checked from the formula text, after one row did not match | 258/258 HD cells -> Exists; Table 4 rows 24/20/38/3,822, 9, 8/6/2 match; one row 6 vs 5, documented; broken case: without a22oi Table 4 fails | |
| L-005 | 27 Oct 2026 | | Claude / claude-opus-5-5 | An AIGER reader and a 4-input cut enumerator with an independent check (`src/aiger.py`, `src/cuts.py`) | Kept | Every cut of the test designs re-simulated per input combination; broken cases: a flipped row and a dropped leaf are both caught; binary and ASCII AIGER agree | |
| L-006 | 27 Oct 2026 | | Claude / claude-opus-5-5 | Step 1 script: design -> AIG (`src/make_aig.sh`) | Changed: removed `-zinit` (mistake M-01) | AIG input count equals the design's real inputs (26 for csa8) | |
| L-007 | 27 Oct 2026 | | Claude / claude-opus-5-5 | The Table 1 runner with the handout's exact commands (`src/table1.py`), the HD class table, per-design stats, Makefile, README, demo | Changed the demo to skip cuts that ignore a leaf (mistake M-02) | Mapping commands run on a test design with Yosys 0.33; Table 1 itself waits for the student pack | |
| L-008 | 28 Oct 2026 | | Claude / claude-opus-5-5 | Run `make all` on the student pack with `yowasp-yosys` 0.33 and fix what fails | Changed `src/designs.py` to resolve `build/given` to its real path (mistake M-03); README records the PDK version and Liberty hash actually used | `make aigs` writes all six AIGs; `make stats` check pass on all six; `make test` 14 OK; Table 1 run, differs (README, Limitations) | |
