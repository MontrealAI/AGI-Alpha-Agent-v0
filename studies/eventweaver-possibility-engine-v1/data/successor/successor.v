module successor_core_0(input wire clk, input wire rst, input wire [7:0] events, output wire [0:0] out);
  reg [14:0] state;
  always @(posedge clk) begin
    if (rst) state <= 15'b0;
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
    end
  end
  assign out[0] = state[14];
endmodule

module successor_core_1(input wire clk, input wire rst, input wire [7:0] events, output wire [0:0] out);
  reg [9:0] state;
  always @(posedge clk) begin
    if (rst) state <= 10'b0;
    else begin
      state[0] <= ~events[3] & ((events[0]));
      state[1] <= ~events[3] & ((state[0]));
      state[2] <= ~events[3] & ((state[0] & events[1]));
      state[3] <= ~events[3] & ((state[2]));
      state[4] <= ~events[3] & ((state[1] & events[1]));
      state[5] <= ~events[3] & ((state[4]));
      state[6] <= ~events[3] & ((state[2] & events[2]));
      state[7] <= ~events[3] & ((state[6]) | (state[3] & events[2]) | (state[4] & events[2]));
      state[8] <= ~events[3] & ((state[7]) | (state[5] & events[2]));
      state[9] <= ~events[3] & ((state[8]));
    end
  end
  assign out[0] = state[9];
endmodule

module successor(input wire clk,input wire rst,input wire [7:0] events,output wire [1:0] out);
  wire [7:0] local_0;
  assign local_0[7:4] = 4'b0;
  assign local_0[0] = events[0];
  assign local_0[1] = events[1];
  assign local_0[2] = events[2];
  assign local_0[3] = events[3];
  successor_core_0 inst_0(.clk(clk),.rst(rst),.events(local_0),.out(out[0]));
  wire [7:0] local_1;
  assign local_1[7:4] = 4'b0;
  assign local_1[0] = out[0];
  assign local_1[1] = events[4];
  assign local_1[2] = events[5];
  assign local_1[3] = events[6];
  successor_core_1 inst_1(.clk(clk),.rst(rst),.events(local_1),.out(out[1]));
endmodule
