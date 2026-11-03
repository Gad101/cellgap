# DRAFT rows for ai/use_log.md and ai/mistakes_log.md  (checkpoint 2, Person A)

Edit these before committing. Fill in your name and commit hashes. Keep a row only if it is
true for you; "How you checked it" must be something you ran or read yourself.

## ai/use_log.md
| ID | Date | Who | Tool and model | What you asked | What you kept or changed | How you checked it | Commit |
|---|---|---|---|---|---|---|---|
| L-A1 | Nov 2 | <name> | Claude (chat) | Cost model for a class: stages, inverters, transistors; area model fitted to HD x1 cells | Kept; added absorption cases after and4 came out at 14T | `costmodel.verify` simulates the formula of all 3,984 classes; hand costs for nand2, and2, a21oi, Appendix A cell, and4 in `test_known_costs` | <hash> |
| L-A2 | Nov 2 | <name> | Claude (chat) | Candidate finder: classify cuts vs HD, exclusive cones, greedy non-overlapping selection, ranking | Kept; added Table 3 area exceptions and a cone-size cap; removed an invented default area | `test_candidates.py` (cones on a hand-built AIG, overlap, loss, request check); remapped the top 5 cells with Yosys | <hash> |
| L-A3 | Nov 2 | <name> | Claude (chat) | Tests and broken cases for the above | Kept | the broken case `wrong_cost_expression.json` must be rejected; `make test` passes | <hash> |

## ai/mistakes_log.md
| ID | Log entry | What was wrong | How you caught it | Would a weaker check have missed it? |
|---|---|---|---|---|
| M-A1 | L-A1 | and4 costed 14T: the Shannon stage kept a redundant literal `(A & g1) | !A` | hand-computed cost in `test_known_costs` (and4 = 12T) | Yes: the formula still simulated correctly, only the cost was wrong |
| M-A2 | L-A1 | inv_1 counted as "multi-stage", polluting the area fit | `test_agrees_with_cmos_for_one_stage_functions` | Yes: the fit still ran and gave plausible numbers |
| M-A3 | L-A2 | Fallback of 2.5 um2 per AND node: an invented area (AGENTS.md rule 3) | re-reading AGENTS.md, not by a check | Yes; now `test_missing_baseline_log_is_an_error_not_a_guess` |
| M-A4 | L-A2 | Table 3's exceptions (Exists with an inverter, Contained kept if cheaper) left out: only New was kept | re-reading handout section 5 against the output | Yes: no test existed; the per-class kept counts are now printed |
| M-A5 | L-A2 | Saving counted every node of an unoptimized AIG cone: top candidate looked 4x better (985 vs 250 um2) | the top cell needed only 3 ANDs but the cones averaged more | Yes: all tests passed. Still a guess: remapping shows the ranking is rough |
