module alu_b_decoder(
    input  [6:0]  opcode,
    input  [2:0]  func3,
    input  [6:0]  func7,
    input  [31:0] rdata,
    input  [63:0] rs_reg,
    output logic [63:0] alu_b
);
    wire [63:0] imm_i = {{52{rdata[31]}}, rdata[31:20]};
    wire [63:0] shamt = {{59{1'b0}}, rdata[24:20]};
    wire [63:0] imm_s = {{52{rdata[31]}}, rdata[31:25], rdata[11:7]};
    wire [63:0] imm_b = {{51{rdata[31]}}, rdata[31], rdata[7], rdata[30:25], rdata[11:8], 1'b0};
    wire [63:0] imm_j = {{43{rdata[31]}}, rdata[31], rdata[19:12], rdata[20], rdata[30:21], 1'b0};
    wire [63:0] imm_u = {{32{rdata[31]}}, rdata[31:12], 12'b0};

    logic [63:0] result;
    assign alu_b = result;

    always_comb begin
        case (opcode)                                                  //srai   //everything else
            OP_IMM: result = (func3 == 3'b101 && func7 == 7'b0100000) ? shamt : imm_i;   // I-type arithmetic (addi, slti, xori...)
            OP_REG: result = rs_reg;   // register arithmetic (add, slt, xor...)
            7'b0011011: result = imm_i;   // W-type I (addiw, slliw...)
            OP_LOAD: result = imm_i;   // loads (lb, lw, ld...)
            OP_JALR: result = imm_i;   // jalr
            OP_STORE: result = imm_s;   // stores (sb, sw, sd...)
            OP_BRANCH: result = imm_b;   // branches (beq, bne...)
            OP_JAL: result = imm_j;   // jal
            OP_LUI: result = imm_u;   // lui
            OP_AUIPC: result = imm_u;   // auipc
            default:    result = rs_reg;  // R-type uses rs2
        endcase
    end
endmodule
