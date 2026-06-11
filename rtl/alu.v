module alu(
    input wire [63:0] a_in,
    input wire [63:0] b_in,
    input wire [63:0] mask_in,
    input wire [3:0] alu_op_in,
    output reg [63:0] result_out
);

    wire [63:0] a = a_in & mask_in;
    wire [63:0] b = b_in & mask_in;
    reg [63:0] result;

    always_comb begin
        case (alu_op_in)
            4'b0000: result = a + b;
            4'b0001: result = a - b;
            4'b0010: result = a & b;
            4'b0011: result = a | b;
            4'b0100: result = a ^ b;
            4'b0101: result = ~(a | b);
            4'b0110: result = a << b;
            4'b0111: result = a >> b;
            default: result = 64'b0;
        endcase
        result_out = result & mask_in;
    end

endmodule
