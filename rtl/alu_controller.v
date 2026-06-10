module alu_controller(
    input [6:0] opcode,
    input [2:0] func3,
    input [6:0] func7,
    output reg [3:0] alu_op
);
always @(*) begin

    alu_op = 4'b0000;

    case (opcode)
        7'h0013:
            case (func3)
                3'b000: alu_op = 4'b0000;
                3'b001: alu_op = 4'b0001;
                3'b010: alu_op = 4'b0010;
                3'b011: alu_op = 4'b0011;
                3'b100: alu_op = 4'b0100;
                3'b101: alu_op = 4'b0101;
                3'b110: alu_op = 4'b0110;
                3'b111: alu_op = 4'b0111;
            endcase
        7'b01: ;
        7'b10: ;
        7'b11: ;
        default: ;
    endcase
end
endmodule
