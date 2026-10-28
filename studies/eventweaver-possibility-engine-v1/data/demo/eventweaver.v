module eventweaver(input wire clk, input wire rst, input wire [7:0] events, output wire [1:0] out);
  reg [28:0] state;
  always @(posedge clk) begin
    if (rst) state <= 29'b0;
    else begin
      state[0] <= ~events[3] & ((events[0]));
      state[1] <= ~events[3] & ((state[0]));
      state[2] <= ~events[3] & ((state[1]));
      state[3] <= ~events[3] & ((state[0] & events[1]));
      state[4] <= ~events[3] & ((state[3]));
      state[5] <= ~events[3] & ((state[1] & events[1]));
      state[6] <= ~events[3] & ((state[5]));
      state[7] <= ~events[3] & ((state[2] & events[1]));
      state[8] <= ~events[3] & ((state[7]));
      state[9] <= ~events[3] & ((state[3] & events[2]));
      state[10] <= ~events[3] & ((state[9]) | (state[4] & events[2]) | (state[5] & events[2]));
      state[11] <= ~events[3] & ((state[10]) | (state[6] & events[2]) | (state[7] & events[2]));
      state[12] <= ~events[3] & ((state[11]) | (state[8] & events[2]));
      state[13] <= ~events[3] & ((state[12]));
      state[14] <= ~events[3] & ((state[13]));
      state[15] <= ~events[7] & ((events[4]));
      state[16] <= ~events[7] & ((state[15]));
      state[17] <= ~events[7] & ((state[15] & events[5]));
      state[18] <= ~events[7] & ((state[17]));
      state[19] <= ~events[7] & ((state[18]));
      state[20] <= ~events[7] & ((state[16] & events[5]));
      state[21] <= ~events[7] & ((state[20]));
      state[22] <= ~events[7] & ((state[21]));
      state[23] <= ~events[7] & ((state[18] & events[6]));
      state[24] <= ~events[7] & ((state[23]) | (state[19] & events[6]) | (state[21] & events[6]));
      state[25] <= ~events[7] & ((state[24]) | (state[22] & events[6]));
      state[26] <= ~events[7] & ((state[25]));
      state[27] <= ~events[7] & ((state[26]));
      state[28] <= ~events[7] & ((state[27]));
    end
  end
  assign out[0] = state[14];
  assign out[1] = state[28];
endmodule
