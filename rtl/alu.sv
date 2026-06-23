import alu_types::*;
import mask_types::*;

module alu(
    input logic [63:0] a_in,
    input logic [63:0] b_in,
    input mask_type_t mask_in,
    input logic [3:0] alu_op_in,
    output logic [63:0] result_out
);

    logic [63:0] mask;
    assign mask = (mask_in == MASK_8_BIT  || mask_in == MASK_8_BIT_EXTENDED)  ? { {56{1'b0}}, {8{1'b1}}  } :
                  (mask_in == MASK_16_BIT || mask_in == MASK_16_BIT_EXTENDED) ? { {48{1'b0}}, {16{1'b1}} } :
                  (mask_in == MASK_32_BIT || mask_in == MASK_32_BIT_EXTENDED) ? { {32{1'b0}}, {32{1'b1}} } :
                  (mask_in == MASK_64_BIT || mask_in == MASK_64_BIT_EXTENDED) ? {64{1'b1}} :
                                                         {64{1'b1}};

    logic is_word;
    assign is_word = (mask_in == MASK_32_BIT || mask_in == MASK_32_BIT_EXTENDED);

    logic is_extended;
    assign is_extended =    mask_in == MASK_8_BIT_EXTENDED ||
                            mask_in == MASK_16_BIT_EXTENDED ||
                            mask_in == MASK_32_BIT_EXTENDED ||
                            mask_in == MASK_64_BIT_EXTENDED;

    logic [63:0] a;
    assign a = a_in & mask;
    logic [63:0] b;
    assign b = b_in & mask;
    logic [63:0] sra_a;
    assign sra_a = is_word ?
        (is_extended ?  {{32{a[31]}}, a[31:0]} :
                        {{32{1'b0}}, a[31:0]})
    : a;
    logic [5:0] shamt;
    assign shamt = is_word ? {1'b0, b[4:0]} : b[5:0];

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
            ALU_SLL: result = a << shamt;
            ALU_SRL: result = a >> shamt;
            ALU_SRA: result = $signed(sra_a) >>> shamt;
            ALU_BYPASS_B: result = b;
            ALU_NOP: result = a;
            default: result = 64'b0;
        endcase
        result_out = is_word ?
            (is_extended ?  {{32{result[31]}}, result[31:0]} :
                            {{32{1'b0}}, result[31:0]})
        : result;
    end

endmodule
