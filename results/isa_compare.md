# risc8, pic16, p16c5x: the same new cells?

| Pair | Candidate classes in both (all) | Jaccard (all) | Shared in top 10 | Jaccard (top 10) |
|---|---|---|---|---|
| risc8 / pic16 | 0 | 0.000 | 0 | 0.000 |
| risc8 / p16c5x | 0 | 0.000 | 0 | 0.000 |
| pic16 / p16c5x | 0 | 0.000 | 0 | 0.000 |

Candidates per design: risc8 0, pic16 0, p16c5x 1.

| Class | risc8 rank (saving um2) | pic16 rank (saving um2) | p16c5x rank (saving um2) |
|---|---|---|---|
| 0x07FF | - | - | 1 (72.63) |

## Most frequent new classes (cuts), top 10 per design

| Pair | Shared in top 10 | Jaccard |
|---|---|---|
| risc8 / pic16 | 7 | 0.538 |
| risc8 / p16c5x | 7 | 0.538 |
| pic16 / p16c5x | 9 | 0.818 |

| Class | risc8 cuts | pic16 cuts | p16c5x cuts |
|---|---|---|---|
| 0x00AB | 2669 | 1960 | 2900 |
| 0x00AE | 2090 | 1853 | 2198 |
| 0x00EA | 1953 | 2060 | 2040 |
| 0x00AC | 1583 | 1525 | 1840 |
| 0x001F | 962 | 1493 | 1470 |
| 0x000E | 1149 | 959 | 1506 |
| 0x88A8 | 896 | 1089 | 1598 |
| 0x03AA | - | 1073 | 1274 |
| 0x888B | - | 1070 | 1275 |
| 0x002A | 1672 | - | - |
| 0x888A | - | 1207 | - |
| 0x88A0 | - | - | 1165 |
| 0x00EF | 951 | - | - |
| 0x001B | 913 | - | - |

A dash means the class is not among that design's top 10 (it may still occur there).
