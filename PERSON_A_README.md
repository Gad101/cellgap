# Person A, checkpoint 2: find, cost and rank candidate cells

Copy these files over your repository (the Makefile replaces yours; it only adds the
targets `area-model` and `candidates`, adds `tests/test_candidates.py` to `make test`,
and adds `candidates` to `make all`). Nothing here edits an existing test, broken case
or the PDK (AGENTS.md rule 1).

| File | What it does (handout step) |
|---|---|
| `src/costmodel.py` | Step 4: stages, inverters, transistors of a class. Step 6: area model fitted to HD's x1 cells, with its error |
| `src/candidates.py` | Steps 3, 5, 7: classify cuts against HD, apply Table 3's area exceptions, measure each occurrence by its exclusive cone, rank |
| `tests/test_candidates.py` | 13 tests; `tests/broken/wrong_cost_expression.json` is the broken case for the cost check |
| `ai/person_A_log_drafts.md` | DRAFT rows for your two AI logs. Edit them to what really happened |

## Run (after `make setup`, `make aigs`, `make table1`)
    make area-model        # results/area_model.json, results/area_model_fit.csv
    make candidates GROUP=g<your group number>
    make test

Outputs in `results/`: `candidates.json` (each entry already has the Appendix A request
fields: name, inputs, output, expression, truth_table, sizing, estimated_area_um2, plus
cost, saving and per-design counts), `redundancy_report.csv` (every class seen, its
Table 3 class, matching HD cell, kept or dropped), `candidate_stats.csv`.

## How it works, in one paragraph
For each design: enumerate cuts, keep the real ones (function uses every leaf, 2+ leaves),
group into P classes, classify each class against HD. Exists is dropped; Exists-with-an-
inverter and Contained are kept only if the estimated area beats the HD cell (+ inv_1).
Each kept class is costed by costmodel.best (literal / one stage with input or output
inverters / Shannon stage, each verified by simulation) and its area estimated from the
fitted model. For every occurrence the exclusive cone is the set of AND nodes that would
disappear. Per design, non-overlapping occurrences with positive saving are picked greedily
and the classes are ranked by total estimated saving.

## Limits (say them in the report, "Limits" section)
* The cost is an upper bound: no inverter sharing, no search of every factoring.
* The area model is a straight line through HD x1 cells; its error is in area_model.json.
  nand4_1 and nor4_1 are left out of the fit (4 in series, outside the project's rule).
* The saving is a guess: m AND nodes x baseline area per AND node, with m capped at the
  smallest cone seen for that function. Real savings come from re-mapping (steps 9-10).
* Baseline area per AND comes from the Table 1 logs. The AIG is made after dffunmap, so
  designs with many enable/reset flip-flops (uart_apb) get a low figure.
* Script A can change a design's area by about +-1% when the library changes even if it
  uses no new cell. Compare with the best of both scripts.
