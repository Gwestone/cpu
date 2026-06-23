import mul_types::*;
import cpu_types::*;

module mul_controller(
    input logic [6:0] opcode,
    input logic [2:0] func3,
    input logic [6:0] func7,
    output mul_op_t mul_op
);

    always_comb begin
        if((opcode == OP_REG || opcode == OP_REG_W) && func3 == 3'b000 && func7 == 7'b0000001)
            mul_op = MUL_MUL;
        else if(opcode == OP_REG && func3 == 3'b001 && func7 == 7'b0000001)
            mul_op = MUL_MUL_H;
        else if(opcode == OP_REG && func3 == 3'b011 && func7 == 7'b0000001)
            mul_op = MUL_MUL_HU;
        else if(opcode == OP_REG && func3 == 3'b010 && func7 == 7'b0000001)
            mul_op = MUL_MUL_HSU;
        else if((opcode == OP_REG || opcode == OP_REG_W) && func3 == 3'b100 && func7 == 7'b0000001)
            mul_op = MUL_DIV;
        else if((opcode == OP_REG || opcode == OP_REG_W) && func3 == 3'b101 && func7 == 7'b0000001)
            mul_op = MUL_DIV_U;
        else if((opcode == OP_REG || opcode == OP_REG_W) && func3 == 3'b110 && func7 == 7'b0000001)
            mul_op = MUL_REM;
        else if((opcode == OP_REG || opcode == OP_REG_W) && func3 == 3'b111 && func7 == 7'b0000001)
            mul_op = MUL_REM_U;
        else
            mul_op = MUL_MUL;

    end

endmodule
