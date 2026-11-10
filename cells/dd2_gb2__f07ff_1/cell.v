module dd2_gb2__f07ff_1(input A, input B, input C, input D, output Y, inout VPWR, VGND, VPB, VNB);
  assign Y = ~((D & (C | (A & B))));
endmodule
