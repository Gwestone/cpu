package alu_types;
    typedef enum logic [3:0] {
        ALU_ADD,
        ALU_SUB,
        ALU_SLL,
        ALU_SRL,
        ALU_SRA,
        ALU_AND,
        ALU_OR,
        ALU_XOR,
        ALU_SLT,
        ALU_SLTU,
        ALU_COPY,
        ALU_NOP,
        ALU_BYPASS_B
    } alu_op_t;
endpackage
