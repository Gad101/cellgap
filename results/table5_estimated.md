# Table 5, estimated areas

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |
|---|---|---|---|---|---|---|
| cpu8 | A | 4186.5 | 4186.5 | 0.00% | 1 | pass |
| cpu8 | B | 4359.2 | 4282.9 | 1.75% | 6 | pass |
| dsp8 | A | 5928.2 | 5914.4 | 0.23% | 10 | pass |
| dsp8 | B | 6214.7 | 6185.9 | 0.46% | 40 | pass |
| arlet6502 | A | 9701.8 | 9654.3 | 0.49% | 3 | pass |
| arlet6502 | B | 9995.8 | 9887.0 | 1.09% | 16 | pass |
| uart_apb | A | 12948.7 | 12939.9 | 0.07% | 0 | pass |
| uart_apb | B | 13180.1 | 13168.9 | 0.08% | 4 | pass |
| risc8 | A | 28263.4 | 28252.1 | 0.04% | 3 | pass |
| risc8 | B | 27511.4 | 27493.9 | 0.06% | 40 | pass |
| fir10 | A | 25968.7 | 25968.7 | 0.00% | 0 | pass |
| fir10 | B | 29055.4 | 28507.3 | 1.89% | 254 | pass |
| spm | A | 2869.0 | 2869.0 | 0.00% | 0 | pass |
| spm | B | 2907.8 | 2946.6 | -1.33% | 31 | pass |
| mul | A | 1756.7 | 1756.7 | 0.00% | 0 | pass |
| mul | B | 1948.1 | 1923.1 | 1.28% | 16 | pass |

Best of both (the smaller of scripts A and B on each side):

| Design | Baseline (um2) | With new cells (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4186.5 | 4186.5 | 0.00% |
| dsp8 | 5928.2 | 5914.4 | 0.23% |
| arlet6502 | 9701.8 | 9654.3 | 0.49% |
| uart_apb | 12948.7 | 12939.9 | 0.07% |
| risc8 | 27511.4 | 27493.9 | 0.06% |
| fir10 | 25968.7 | 25968.7 | 0.00% |
| spm | 2869.0 | 2869.0 | 0.00% |
| mul | 1756.7 | 1756.7 | 0.00% |
| **Total, required designs** | **86245.3** | **86157.7** | **0.10%** |

Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; with new cells: libs/hd_reduced_plus_new_cells_est.lib. Equivalence: ABC cec against the RTL (dsec for designs with flip-flops), results/mapping_equivalence.csv. SPM and mul also pass Tutorial 4's gate-level testbenches: results/gate_level_testbenches.csv.
