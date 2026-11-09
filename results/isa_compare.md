# risc8, pic16, p16c5x: the same new cells?

| Pair | Candidate classes in both (all) | Jaccard (all) | Shared in top 10 | Jaccard (top 10) |
|---|---|---|---|---|
| risc8 / pic16 | 0 | 0.000 | 0 | 0.000 |
| risc8 / p16c5x | 1 | 0.167 | 1 | 0.167 |
| pic16 / p16c5x | 0 | 0.000 | 0 | 0.000 |

Candidates per design: risc8 6, pic16 0, p16c5x 1.

| Class | risc8 rank (saving um2) | pic16 rank (saving um2) | p16c5x rank (saving um2) |
|---|---|---|---|
| 0x07FF | 4 (6.22) | - | 1 (72.63) |
| 0xAAEF | 1 (61.48) | - | - |
| 0xEABF | 2 (28.28) | - | - |
| 0xEAEF | 3 (6.68) | - | - |
| 0xAAAB | 5 (1.97) | - | - |
| 0xEBEB | 6 (0.61) | - | - |

## Most frequent new classes (cuts), top 10 per design

| Pair | Shared in top 10 | Jaccard |
|---|---|---|
| risc8 / pic16 | 4 | 0.250 |
| risc8 / p16c5x | 4 | 0.250 |
| pic16 / p16c5x | 9 | 0.818 |

| Class | risc8 cuts | pic16 cuts | p16c5x cuts |
|---|---|---|---|
| 0x00AB | 786 | 1960 | 2900 |
| 0x00AE | 825 | 1853 | 2198 |
| 0x00EA | - | 2060 | 2040 |
| 0x001F | 762 | 1493 | 1470 |
| 0x88A8 | 678 | 1089 | 1598 |
| 0x00AC | - | 1525 | 1840 |
| 0x000E | - | 959 | 1506 |
| 0x03AA | - | 1073 | 1274 |
| 0x888B | - | 1070 | 1275 |
| 0x002A | 1876 | - | - |
| 0x888A | - | 1207 | - |
| 0x88A0 | - | - | 1165 |
| 0x00EF | 1105 | - | - |
| 0x008F | 700 | - | - |
| 0x078F | 638 | - | - |
| 0xA8FD | 623 | - | - |
| 0x008A | 539 | - | - |

A dash means the class is not among that design's top 10 (it may still occur there).
