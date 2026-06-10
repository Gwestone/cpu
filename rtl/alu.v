module alu(
    input wire [63:0] a,
    input wire [63:0] b,
    input wire [3:0] alu_op,
    output reg [63:0] result
);

    always @(*) begin
        case (alu_op)
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
    end

endmodule
