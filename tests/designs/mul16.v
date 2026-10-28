// Test design written for this repository: a 16x16 combinational multiplier,
// used only to time the cut enumerator on a few thousand AND nodes.
module mul16 (input [15:0] a, b, output [31:0] y);
  assign y = a * b;
endmodule
