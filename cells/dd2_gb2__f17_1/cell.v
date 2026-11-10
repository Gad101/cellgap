module dd2_gb2__f17_1(input A, input B, input C, output Y, inout VPWR, VGND, VPB, VNB);
  assign Y = ~(((A & B) | (C & (A | B))));
endmodule
