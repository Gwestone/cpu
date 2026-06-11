module alu_b_decoder(
    input  [6:0]  opcode,
    input  [31:0] rdata,
    input  [63:0] rs_reg,
    output reg [63:0] alu_b
);
    wire [63:0] imm_i = {{52{rdata[31]}}, rdata[31:20]};
    wire [63:0] imm_s = {{52{rdata[31]}}, rdata[31:25], rdata[11:7]};
    wire [63:0] imm_b = {{51{rdata[31]}}, rdata[31], rdata[7], rdata[30:25], rdata[11:8], 1'b0};
    wire [63:0] imm_j = {{43{rdata[31]}}, rdata[31], rdata[19:12], rdata[20], rdata[30:21], 1'b0};
    wire [63:0] imm_u = {{32{rdata[31]}}, rdata[31:12], 12'b0};

    always_comb begin
        case (opcode)
            7'b0010011: alu_b = imm_i;   // I-type arithmetic (addi, slti, xori...)
            7'b0011011: alu_b = imm_i;   // W-type I (addiw, slliw...)
            7'b0000011: alu_b = imm_i;   // loads (lb, lw, ld...)
            7'b1100111: alu_b = imm_i;   // jalr
            7'b0100011: alu_b = imm_s;   // stores (sb, sw, sd...)
            7'b1100011: alu_b = imm_b;   // branches (beq, bne...)
            7'b1101111: alu_b = imm_j;   // jal
            7'b0110111: alu_b = imm_u;   // lui
            7'b0010111: alu_b = imm_u;   // auipc
            default:    alu_b = rs_reg;  // R-type uses rs2
        endcase
    end
endmodule
