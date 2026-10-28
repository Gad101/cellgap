// Test design written for this repository: a 4-bit ALU with a mux tree.
module mux_alu4 (input [3:0] a, b, input [1:0] op, output reg [3:0] y);
  always @* case (op)
    2'b00: y = a & b;
    2'b01: y = a | b;
    2'b10: y = a ^ b;
    default: y = a + b;
  endcase
endmodule
