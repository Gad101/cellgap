# Broken cases

Every check must be shown to fail on a deliberately broken case (overview,
section 4.3, rule 3). AI tools must not edit this folder (AGENTS.md).

| File | Check it breaks | Expected result |
|---|---|---|
| `wrong_cut_table.json` | cut check (`src/cuts.py --check`) | one cut gets a truth table with one row flipped; the check must report it |
| `not_a_cut.json` | cut check | one cut loses a leaf, so it no longer cuts its node off from the inputs; the check must report it |
| `hd_missing_cells.json` | redundancy self-test (`src/redundancy.py selftest`) | the self-test is run without some HD cells; the Table 4 comparison must fail |
| `wrong_expression.json` | expression / truth-table check | an expression whose stated truth table is wrong; it must be refused |
