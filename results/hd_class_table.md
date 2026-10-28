# Class table of sky130_fd_sc_hd (single-output combinational cells)

Class = smallest 16-bit truth table up to input order and output inversion (PO).
`one_stage_T`: transistors of one static CMOS stage for the class (Y or !Y),
at most 3 in series; empty = needs more than one stage.

- 258 cells with <= 4 inputs, in 29 PO classes and 13 NPN classes
- 66 cells with 5 or 6 inputs (used only by the Contained test): a2111o a2111oi a221o a221oi a222oi a311o a311oi a32o a32oi a41o a41oi mux4 o2111a o2111ai o221a o221ai o311a o311ai o32a o32ai o41a o41ai

| po_class | inputs_used | p_classes | npn_class | one_stage_T | families | n_cells | min_area_um2 |
|---|---|---|---|---|---|---|---|
| 0x0000 | 0 | 0x0000 0xFFFF | 0x0000 |  | macro_sparecell | 1 | 36.2848 |
| 0x00FF | 1 | 0x00FF 0xAAAA | 0x00FF | 2 | buf bufbuf bufinv clkbuf clkdlybuf4s15 clkdlybuf4s18 clkdlybuf4s25 clkdlybuf4s50 clkinv clkinvlp dlygate4sd1 dlygate4sd2 dlygate4sd3 dlymetal6s2s dlymetal6s4s dlymetal6s6s inv lpflow_clkbufkapwr lpflow_clkinvkapwr lpflow_lsbuf_lh_hl_isowell_tap lpflow_lsbuf_lh_isowell lpflow_lsbuf_lh_isowell_tap probe_p probec_p | 63 | 3.7536 |
| 0x000F | 2 | 0x000F 0xEEEE | 0x000F | 4 | lpflow_inputiso1p nor2 or2 | 9 | 3.7536 |
| 0x00AA | 2 | 0x00AA 0xAAFF | 0x000F |  | and2b lpflow_inputiso0p lpflow_inputiso1n lpflow_isobufsrc lpflow_isobufsrckapwr nand2b nor2b or2b | 20 | 6.256 |
| 0x0FF0 | 2 | 0x0FF0 0x9999 | 0x0FF0 |  | xnor2 xor2 | 6 | 8.7584 |
| 0x0FFF | 2 | 0x0FFF 0x8888 | 0x000F | 4 | and2 lpflow_inputiso0n nand2 | 9 | 3.7536 |
| 0x0003 | 3 | 0x0003 0xFEFE | 0x0003 | 6 | nor3 or3 | 6 | 5.0048 |
| 0x000A | 3 | 0x000A 0xEEFF | 0x0003 |  | nor3b or3b | 6 | 7.5072 |
| 0x003F | 3 | 0x003F 0xEAEA | 0x003F | 6 | a21o a21oi | 6 | 5.0048 |
| 0x0088 | 3 | 0x0088 0xAFFF | 0x0003 |  | and3b nand3b | 6 | 7.5072 |
| 0x00EE | 3 | 0x00EE 0xAAAF | 0x003F |  | o21ba o21bai | 6 | 7.5072 |
| 0x033F | 3 | 0x033F 0xE8E8 | 0x033F | 10 | maj3 | 3 | 10.0096 |
| 0x03CF | 3 | 0x03CF 0xAACC | 0x03CF |  | mux2 mux2i | 7 | 10.0096 |
| 0x03FF | 3 | 0x03FF 0xA8A8 | 0x003F | 6 | o21a o21ai | 7 | 5.0048 |
| 0x0AAA | 3 | 0x0AAA 0x88FF | 0x003F |  | a21bo a21boi | 7 | 7.5072 |
| 0x3CC3 | 3 | 0x3CC3 0x9696 | 0x3CC3 |  | xnor3 xor3 | 6 | 22.5216 |
| 0x3FFF | 3 | 0x3FFF 0x8080 | 0x0003 | 6 | and3 nand3 | 6 | 5.0048 |
| 0x0001 | 4 | 0x0001 0xFFFE | 0x0001 |  | nor4 or4 | 6 | 6.256 |
| 0x0002 | 4 | 0x0002 0xFEFF | 0x0001 |  | nor4b or4b | 6 | 8.7584 |
| 0x0007 | 4 | 0x0007 0xFEEE | 0x0007 | 8 | a211o a211oi | 6 | 7.5072 |
| 0x0008 | 4 | 0x0008 0xEFFF | 0x0001 |  | and4bb nand4bb nor4bb or4bb | 12 | 10.0096 |
| 0x007F | 4 | 0x007F 0xEAAA | 0x007F | 8 | a31o a31oi | 6 | 6.256 |
| 0x0080 | 4 | 0x0080 0xBFFF | 0x0001 |  | and4b nand4b | 6 | 8.7584 |
| 0x01FF | 4 | 0x01FF 0xAAA8 | 0x007F | 8 | o31a o31ai | 6 | 7.5072 |
| 0x0357 | 4 | 0x0357 0xEEE0 | 0x0357 | 8 | o22a o22ai | 6 | 6.256 |
| 0x0777 | 4 | 0x0777 0xEAC0 | 0x0357 | 8 | a22o a22oi | 6 | 7.5072 |
| 0x0EEE | 4 | 0x0EEE 0x888F | 0x0357 |  | a2bb2o a2bb2oi o2bb2a o2bb2ai | 12 | 8.7584 |
| 0x1FFF | 4 | 0x1FFF 0x8880 | 0x0007 | 8 | o211a o211ai | 6 | 7.5072 |
| 0x7FFF | 4 | 0x7FFF 0x8000 | 0x0001 |  | and4 nand4 | 6 | 6.256 |
