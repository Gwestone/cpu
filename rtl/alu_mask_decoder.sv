module alu_mask_decoder (
    input  [6:0] opcode,
    input  [2:0] func3,    // unused — mask depends only on opcode
    input  [6:0] func7,    // unused
    output logic [63:0] alu_mask
);
    always_comb begin
        case (opcode)
            7'b0011011: alu_mask = {32'b0, {32{1'b1}}};  // W-type I — 32-bit mask
            7'b0111011: alu_mask = {32'b0, {32{1'b1}}};  // W-type R — 32-bit mask
            default:    alu_mask = {64{1'b1}};            // everything else — full 64-bit
        endcase
    end
endmodule
