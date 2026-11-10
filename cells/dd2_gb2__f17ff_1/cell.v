module dd2_gb2__f17ff_1(input A, input B, input C, input D, output Y, inout VPWR, VGND, VPB, VNB);
  assign Y = ~((D & ((A & B) | (C & (A | B)))));
endmodule
