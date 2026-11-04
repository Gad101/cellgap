# Broken cases

Every check must be shown to fail on a deliberately broken case (overview,
section 4.3, rule 3). AI tools must not edit this folder (AGENTS.md).

## wrong_cut_table.json
- Checks: every cut's truth table is correct
- Broken: one row of a truth table is flipped
- Must: report the wrong row

## not_a_cut.json
- Checks: every cut really is a cut
- Broken: one input is removed from a cut
- Must: report it is no longer a cut

## hd_missing_cells.json
- Checks: our HD comparison matches the handout's Table 4
- Broken: some HD cells are left out
- Must: no longer match Table 4

## wrong_expression.json
- Checks: a request's formula and truth table agree
- Broken: the truth table doesn't match the formula
- Must: refuse the request

## wrong_cost_expression.json
- Checks: each cost formula computes its function
- Broken: the formula computes a different function
- Must: reject it

## tests/test_abc_after.py
- Checks: the circuit after ABC cleanup still works the same
- Broken: one gate input is flipped
- Must: ABC says the circuits differ

## tests/test_liberty_with_new_cells.py
- Checks: Yosys reads our Liberty file, with all 189 + new celutes the right function
- Broken (3 cases): an unclosed quote; a missing brace; a formula using an input the cell doesn't have
- Must: Yosys refuses the file; the cell count is wrong; the b

## tests/test_mapping_equivalence.py
- Checks: every mapped design does exactly what the original Verilog does
- Broken: one NAND gate swapped for a NOR gate (in the multipl
- Must: ABC says the design is different

## tests/test_gate_level_testbenches.py
- Checks: the mapped multiplier passes its testbench
- Broken: one NAND gate swapped for a NOR gate
- Must: the testbench fails
