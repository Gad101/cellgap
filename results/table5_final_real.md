# Table 5, final set, real areas

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence | Worst delay base / new (ns) |
|---|---|---|---|---|---|---|---|
| cpu8 | A | 4186.5 | 4186.5 | 0.00% | 0 | pass | 4.1754 / 4.1754 |
| cpu8 | B | 4359.2 | 4279.1 | 1.84% | 0 | pass | 4.1108 / 4.2652 |
| dsp8 | A | 5928.2 | 5928.2 | 0.00% | 0 | pass | 5.2175 / 5.2175 |
| dsp8 | B | 6214.7 | 6216.0 | -0.02% | 0 | pass | 5.6287 / 5.4544 |
| arlet6502 | A | 9701.8 | 9701.8 | 0.00% | 0 | pass | 7.1104 / 7.1104 |
| arlet6502 | B | 9995.8 | 9930.8 | 0.65% | 0 | pass | 8.6488 / 6.2703 |
| uart_apb | A | 12948.7 | 12948.7 | 0.00% | 0 | pass | 6.7771 / 6.7771 |
| uart_apb | B | 13180.1 | 13183.9 | -0.03% | 0 | pass | 4.4893 / 4.4893 |
| risc8 | A | 28263.4 | 28263.4 | 0.00% | 0 | pass | 15.9846 / 15.9846 |
| risc8 | B | 27511.4 | 27505.1 | 0.02% | 0 | pass | 13.3222 / 13.5038 |
| fir10 | A | 25968.7 | 25968.7 | 0.00% | 0 | pass | 6.2563 / 6.2563 |
| fir10 | B | 29055.4 | 29044.1 | 0.04% | 2 | pass | 6.2349 / 6.3212 |
| spm | A | 2869.0 | 2869.0 | 0.00% | 0 | pass | 0.7430 / 0.7430 |
| spm | B | 2907.8 | 2907.8 | 0.00% | 0 | pass | 0.6585 / 0.6585 |
| mul | A | 1756.7 | 1756.7 | 0.00% | 0 | pass | 4.2691 / 4.2691 |
| mul | B | 1948.1 | 1988.2 | -2.06% | 0 | pass | 4.7852 / 5.0705 |

Best of both (the smaller of scripts A and B on each side):

| Design | Baseline (um2) | With new cells (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4186.5 | 4186.5 | 0.00% |
| dsp8 | 5928.2 | 5928.2 | 0.00% |
| arlet6502 | 9701.8 | 9701.8 | 0.00% |
| uart_apb | 12948.7 | 12948.7 | 0.00% |
| risc8 | 27511.4 | 27505.1 | 0.02% |
| fir10 | 25968.7 | 25968.7 | 0.00% |
| spm | 2869.0 | 2869.0 | 0.00% |
| mul | 1756.7 | 1756.7 | 0.00% |
| **Total, required designs** | **86245.3** | **86239.0** | **0.01%** |

Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; with new cells: libs/hd_reduced_plus_final_set_real.lib. Equivalence: ABC cec against the RTL (dsec with flip-flops), results/final/mapping_equivalence_final.csv.
