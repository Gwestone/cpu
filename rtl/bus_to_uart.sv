module bus_to_uart (
    input clk,
    input reset,
    input [7:0] bus,
    output logic tx
);

logic [2:0] bus_pointer;

initial begin
    bus_pointer = 3'h0;
end

always_ff @(posedge clk) begin
    tx <= bus[bus_pointer];
    if (reset) begin
        bus_pointer <= 3'h0;
    end else begin
        bus_pointer <= bus_pointer + 3'h1;
    end
end


endmodule
