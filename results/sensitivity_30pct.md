# Sensitivity: dd2_gb2__f17_1 made 30% smaller

Cell area 8.7584 -> 6.1309 um2. Other cells unchanged.

| Design | Script | Area, estimate (um2) | Area, scaled (um2) | Change | Instances est -> scaled |
|---|---|---|---|---|---|
| cpu8 | A | 4186.5 | 4186.5 | +0.0 | 0 -> 0 |
| cpu8 | B | 4282.9 | 4280.2 | -2.7 | 0 -> 1 |
| dsp8 | A | 5914.4 | 5914.4 | +0.0 | 0 -> 0 |
| dsp8 | B | 6169.7 | 6067.1 | -102.6 | 27 -> 40 |
| arlet6502 | A | 9654.3 | 9654.3 | -0.0 | 0 -> 0 |
| arlet6502 | B | 9884.5 | 9865.0 | -19.5 | 5 -> 6 |
| uart_apb | A | 12939.9 | 12939.9 | +0.0 | 0 -> 0 |
| uart_apb | B | 13170.1 | 13170.1 | +0.0 | 0 -> 0 |
| risc8 | A | 28252.1 | 28252.1 | -0.0 | 0 -> 0 |
| risc8 | B | 27438.8 | 27436.9 | -1.9 | 3 -> 5 |
| fir10 | A | 25968.7 | 25968.7 | -0.0 | 0 -> 0 |
| fir10 | B | 28446.0 | 27258.3 | -1187.7 | 237 -> 403 |

Total best-of-both over the required designs: 86102.6 -> 86100.7 um2 (-1.9).
