# Table 5, final set, est areas

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
