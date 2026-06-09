`timescale 1ns / 1ps

module main(clk, data, reset, message);

    input wire clk;
    input wire reset;
    input wire [7:0] data;

    output reg [7:0] message;

    reg [7:0] message_reg;

    always @(posedge clk) begin
        if (reset) begin
            message_reg <= 0;
        end else begin
            message_reg <= data;
        end
    end

    assign message = message_reg;

endmodule
