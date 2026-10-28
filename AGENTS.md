# AGENTS.md: rules for any AI assistant working in this repository

This repository is DD2 Project 1, Option 2: Finding Cells Worth Adding
(CSCE 3304, Fall 2026). AI is used here as a **development aid** only
(overview section 4.1): no AI model runs when the tool runs, and the same
input always gives the same output.

## What the project is
A tool that reads synthesized designs as and-inverter graphs (AIGs), finds the
small functions (cuts of up to 4 inputs) that appear again and again, checks
which ones the sky130_fd_sc_hd (HD) library already has, and measures what new
cells would save in area when Yosys maps the designs.

## How the project is checked
- `make check`: tool versions (Python >= 3.11, Yosys 0.33 or newer) and the
  paths that `make setup` links (HD Liberty, student pack).
- `make test`: every self-test and every broken case. It must pass on a clean
  checkout. A check that has no broken case does not count as a check.
- Pass or fail comes from these scripts, never from an assistant's opinion.
- Target numbers come from the handouts and must be reproduced, not adjusted:
  - Option 2 handout Table 1 (baseline areas, script A and B);
  - Option 2 handout Table 4 (24 Exists, 20 Exists with an inverter,
    38 Contained, 3,822 New, 9 New one-stage, 5 New one-stage small,
    8 read-once one-stage of which 6 Exist and 2 Contained).

## Conventions
- Truth tables: 16-bit integers. Bit i is Y for the input combination in which
  input k equals bit k of i; input A (index 0) is the least significant input
  (overview Appendix A). A = 0xAAAA, B = 0xCCCC, C = 0xF0F0, D = 0xFF00.
- Classes for CMOS are taken up to input order and output inversion (step 3 of
  the Option 2 handout). NPN classes are counted too, but NPN treats input
  inverters as free and CMOS does not.
- Every number in the reports comes from a file in `results/` that the flow
  wrote.

## What an assistant must NOT do
1. Do not edit anything in `tests/broken/`, the check scripts in `tests/`, the
   PDK, or the files given in the student pack.
2. Do not change a target number from the handout to make a test pass. If a
   number does not match, report the mismatch and stop.
3. Do not invent design-rule, area or timing values. Areas come from the HD
   Liberty file.
4. Do not add network access, randomness without a fixed seed, or an AI call to
   the tool itself.
5. Do not commit the PDK, copies of given files, `build/`, or any file over
   50 MB.

## When an assistant helps
- Say which files you changed and why.
- Every AI-assisted commit carries the trailer `AI-assisted: <tool>/<model>`.
- Each request is logged in `ai/use_log.md`; each mistake a check caught is
  logged in `ai/mistakes_log.md`.
- Both group members must be able to explain every line, including AI-written
  ones: keep functions short and commented.
