import alu_types::*;
import mask_types::*;

module alu_mask_decoder (
    input  [6:0] opcode,
    input  [2:0] func3,    // unused — mask depends only on opcode
    input  [6:0] func7,    // unused
    output mask_type_t alu_mask
);
    always_comb begin
        case (opcode)
            OP_IMM_W: alu_mask = MASK_32_BIT_EXTENDED;  // W-type I — 32-bit mask
            OP_REG_W: alu_mask = MASK_32_BIT_EXTENDED;  // W-type R — 32-bit mask
            default:  alu_mask = MASK_64_BIT;  // everything else — full 64-bit
        endcase
    end
endmodule
