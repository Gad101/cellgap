# Broken cases

Every check must be shown to fail on a deliberately broken case (overview,
section 4.3, rule 3). AI tools must not edit this folder (AGENTS.md).

| File | Check it breaks | Expected result |
|---|---|---|
| `wrong_cut_table.json` | cut check (`src/cuts.py --check`) | one cut gets a truth table with one row flipped; the check must report it |
| `not_a_cut.json` | cut check | one cut loses a leaf, so it no longer cuts its node off from the inputs; the check must report it |
| `hd_missing_cells.json` | redundancy self-test (`src/redundancy.py selftest`) | the self-test is run without some HD cells; the Table 4 comparison must fail |
| `wrong_expression.json` | expression / truth-table check | an expression whose stated truth table is wrong; it must be refused |
| `tests/test_abc_after.py` (`BROKEN_AND = 40`) | after-ABC equivalence check (`src/aig_equiv.sh`, ABC `cec`) | csa8 with the first input of AND number 40 inverted; `cec` must report the two graphs are not equivalent |
| `tests/test_liberty_with_new_cells.py` (`BROKEN_QUOTE`) | Liberty loads in Yosys (`src/write_liberty_with_new_cells.py`) | one new cell with an unclosed quote; Yosys must reject the file |
| `tests/test_liberty_with_new_cells.py` (`BROKEN_BRACE`) | Yosys imports 189 + N cell types (`src/write_liberty_with_new_cells.py`) | one new cell missing its closing brace; Yosys 0.33 reads only part of the file, so the count check must fail |
| `tests/test_liberty_with_new_cells.py` (`BROKEN_FUNCTION`) | new cell functions match their requests (`src/write_liberty_with_new_cells.py`) | one function uses pin E, which the cell lacks; the function check must report it |
| `tests/test_mapping_equivalence.py` (`BROKEN_SWAP`) | every mapping equals the RTL (`src/check_mapping_equivalence.py`: ABC `cec`, or `dsec` with flip-flops) | the first nand2_1 of a netlist swapped for a nor2_1, in mul (`cec`) and cpu8 (`dsec`); both must be rejected |
| `tests/test_gate_level_testbenches.py` (`BROKEN_SWAP`) | SPM/mul gate-level testbenches (`src/run_gate_level_testbenches.py`) | mul netlist with one nand2_1 swapped for a nor2_1; mul_exhaustive_tb must report MISMATCH and fail |

