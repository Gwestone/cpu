import alu_types::*;
import mask_types::*;

module mul_mask_decoder (
    input  [6:0] opcode,
    input  [2:0] func3,
    input  [6:0] func7,
    output mask_type_t mul_mask
);
    // M-extension ops: func7 == 7'b0000001.
    // DIV/REM family has func3[2]==1; func3[0]==0 -> signed, ==1 -> unsigned.
    logic is_mdiv, is_unsigned;
    always_comb begin
        is_mdiv     = (func7 == 7'b0000001) && func3[2];          // DIV/DIVU/REM/REMU
        is_unsigned = is_mdiv && func3[0];                        // DIVU/REMU
    end

    always_comb begin
        unique case (opcode)
            OP_REG_W: begin
                // 32-bit word ops
                mul_mask = is_unsigned ? MASK_32_BIT          // unsigned (divuw/remuw)
                                       : MASK_32_BIT_EXTENDED; // signed   (divw/remw)
            end
            OP_REG: begin
                // 64-bit ops
                mul_mask = is_unsigned ? MASK_64_BIT           // unsigned
                                       : MASK_64_BIT_EXTENDED; // signed
            end
            default: mul_mask = MASK_64_BIT_EXTENDED;          // default to signed
        endcase
    end
endmodule
