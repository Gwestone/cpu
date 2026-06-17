import cpu_types::*;
import alu_types::*;

module alu_controller(
    input [6:0] opcode,
    input [2:0] func3,
    input [6:0] func7,
    output alu_op_t alu_op
);
    always_comb begin

        alu_op = ALU_ADD;

        case (opcode)
            OP_IMM:
                unique case (func3)
                    3'b000: alu_op = ALU_ADD;
                    3'b001: alu_op = ALU_SLL;
                    3'b010: alu_op = ALU_SLT;
                    3'b011: alu_op = ALU_SLTU; // sltiu
                    3'b100: alu_op = ALU_XOR;
                    3'b101: alu_op = (func7[5]) ? ALU_SRA : ALU_SRL;
                    3'b110: alu_op = ALU_OR;
                    3'b111: alu_op = ALU_AND;
                endcase
            OP_REG: begin
                unique case (func3)
                    3'b000: alu_op = (func7[5]) ? ALU_SUB : ALU_ADD;  // sub if func7=0100000, else add
                    3'b001: alu_op = ALU_SLL;                          // sll
                    3'b010: alu_op = ALU_SLT;                          // slt
                    3'b011: alu_op = ALU_SLTU;                         // sltu
                    3'b100: alu_op = ALU_XOR;                          // xor
                    3'b101: alu_op = (func7[5]) ? ALU_SRA : ALU_SRL;  // sra if func7=0100000, else srl
                    3'b110: alu_op = ALU_OR;                           // or
                    3'b111: alu_op = ALU_AND;                          // and
                    default: alu_op = ALU_ADD;
                endcase
            end
            7'b0011011: //addiw style instructions
                unique case (func3)
                    3'b000: alu_op = ALU_ADD; //addiw
                    3'b001: alu_op = ALU_SLL; //slliw
                    3'b101: alu_op = ALU_SRL; //srliw
                    3'b011: alu_op = ALU_XOR;
                    3'b100: alu_op = ALU_AND;
                    3'b110: alu_op = ALU_OR;
                    3'b111: alu_op = ALU_SRA;
                    default: alu_op = ALU_NOP;
                endcase
            7'b0111011:
                if(func3 == 3'b000 && func7 == 7'b0000000) alu_op = ALU_ADD; //addw
                else if(func3 == 3'b000 && func7 == 7'b0100000) alu_op = ALU_SUB; //subw
                else if(func3 == 3'b001 && func7 == 7'b0000000) alu_op = ALU_SLL; //sllw
                else if(func3 == 3'b101 && func7 == 7'b0000000) alu_op = ALU_SRL; //srlw
                else if(func3 == 3'b101 && func7 == 7'b0100000) alu_op = ALU_SRA; //sraw
            OP_LUI: alu_op = ALU_BYPASS_B; //lui - set reg[rd] to imm_u
            OP_AUIPC: alu_op = ALU_BYPASS_B; //auipc - set pc to pc + imm_u
            OP_BRANCH: alu_op = ALU_BYPASS_B; //branch - set pc to pc + imm_b
            OP_LOAD: alu_op = ALU_ADD; //load - set reg[rd] to mem[rs1 + imm_i]
            default: ;
        endcase
    end
endmodule
