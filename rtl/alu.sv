import alu_types::*;

module alu(
    input logic [63:0] a_in,
    input logic [63:0] b_in,
    //TODO remake mask to be enum
    input logic [63:0] mask_in,
    input logic [3:0] alu_op_in,
    output logic [63:0] result_out
);

    logic is_word;
    assign is_word = (mask_in == 64'h00000000FFFFFFFF);
    logic [63:0] a;
    assign a = a_in & mask_in;
    logic [63:0] b;
    assign b = b_in & mask_in;
    logic [63:0] sra_a;
    assign sra_a = is_word ? {{32{a[31]}}, a[31:0]} : a;
    logic [63:0] sra_b;
    assign sra_b = is_word ? {{32{1'b0}}, b[31:0]} : b;

    logic [63:0] result;

    always_comb begin
        case (alu_op_in)
            ALU_ADD: result = a + b;
            ALU_SUB: result = a - b;
            ALU_AND: result = a & b;
            ALU_OR: result = a | b;
            ALU_XOR: result = a ^ b;
            ALU_SLT: result = {{63{1'b0}}, $signed(a) < $signed(b)};
            ALU_SLTU: result = {{63{1'b0}}, $unsigned(a) < $unsigned(b)};
            ALU_SLL: result = a << b;
            ALU_SRL: result = a >> b;
            ALU_SRA: result = $signed(sra_a) >>> sra_b;
            ALU_BYPASS_B: result = b;
            ALU_NOP: result = a;
            default: result = 64'b0;
        endcase
        result_out = result & mask_in;
    end

endmodule
