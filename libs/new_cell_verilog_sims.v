// Simulation models of the new cells (src/write_new_cell_verilog_sims.py)
`timescale 1ns/1ps

module dd2_gb2__feefa_1 (input A, B, C, D, output Y);
  assign Y = !((!A & (!((D & (B)) | (!D & (C))))));
endmodule

module dd2_gb2__f8ae6_1 (input A, B, C, D, output Y);
  assign Y = !((B & (!((D & (A)) | (!D & (!((A & !C))))))) | (!B & (!((A & (!((C & D))))))));
endmodule

module dd2_gb2__f17_1 (input A, B, C, output Y);
  assign Y = !(((A & B) | (C & (A | B))));
endmodule

module dd2_gb2__f077f_1 (input A, B, C, D, output Y);
  assign Y = !(((C | D) & ((A & B) | (C & D))));
endmodule

module dd2_gb2__f17ff_1 (input A, B, C, D, output Y);
  assign Y = !((D & ((A & B) | (C & (A | B)))));
endmodule

module dd2_gb2__fbcc4_1 (input A, B, C, D, output Y);
  assign Y = !((B & (!((A & (((C | D)))) | (!A & (!((C & D))))))) | (!B & (!((C & D)))));
endmodule

module dd2_gb2__f07ff_1 (input A, B, C, D, output Y);
  assign Y = !((D & (C | (A & B))));
endmodule

module dd2_gb2__faabf_1 (input A, B, C, D, output Y);
  assign Y = !((!A & (D | (B & C))));
endmodule

module dd2_gb2__f0bbf_1 (input A, B, C, D, output Y);
  assign Y = !(((C | D) & ((!A & B) | (C & D))));
endmodule

module dd2_gb2__f2bff_1 (input A, B, C, D, output Y);
  assign Y = !((D & ((!A & B) | (C & (!A | B)))));
endmodule

module dd2_gb2__f0eef_1 (input A, B, C, D, output Y);
  assign Y = !(((C | D) & ((!A & !B) | (C & D))));
endmodule
