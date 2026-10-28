// Test design written for this repository (not from the student pack):
// an 8-bit carry-save accumulator with a registered sum, so the AIG has
// latches, majority functions (carries) and 3-input XORs (sums).
module csa8 (input clk, input rst_n, input [7:0] a, b, c, output [8:0] y);
  reg [7:0] s, k;
  wire [7:0] sum = a ^ b ^ c;
  wire [7:0] car = (a & b) | (c & (a | b));
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin s <= 0; k <= 0; end
    else begin s <= sum; k <= car; end
  assign y = {1'b0, s} + {k, 1'b0};
endmodule
