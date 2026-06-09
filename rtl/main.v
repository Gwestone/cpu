module main(
    input wire clk,
    input wire reset,
    output reg [63:0] raddr,
    input wire [63:0] rdata,
    output reg [63:0] waddr,
    output reg [63:0] wdata);

    reg [63:0] pc;
    reg [6:0] opcode;
    reg [2:0] func3;
    reg [6:0] func7;
    reg [4:0] rs1;
    reg [4:0] rs2;
    reg [4:0] rd;
    reg [11:0] imm;
    reg [63:0] registers [0:31];

    always @(posedge clk) begin
        if(reset) begin
            pc <= 0;
            for (integer i = 0; i < 32; i = i + 1) begin
                registers[i] <= 0;
            end
            opcode <= 0;
            func3 <= 0;
            func7 <= 0;
            rs1 <= 0;
            rs2 <= 0;
            rd <= 0;
            imm <= 0;
            raddr <= 0;
        end else begin
            opcode <= rdata[6:0];
            func3 <= rdata[14:12];
            func7 <= rdata[31:25];
            rs1 <= rdata[19:15];
            rs2 <= rdata[24:20];
            rd <= rdata[11:7];
            imm <= rdata[31:20];
            raddr <= pc;
            case(opcode)
                7'b00: pc <= pc + 4;
                7'b0010011: begin
                    case (func3)
                        3'b000: registers[rd] <= registers[rs1] + 64'(imm);
                        3'b001: ;
                        3'b010: ;
                        3'b011: ;
                        3'b100: ;
                        3'b101: ;
                        3'b110: ;
                        3'b111: ;
                    endcase
                    pc <= pc + 4;
                end
                7'b0100011: begin
                    case (func3)
                        3'b000: ;
                        3'b001: ;
                        3'b010: ;
                        3'b011: begin
                            waddr <= registers[rs1] + 64'(imm);
                            wdata <= registers[rs2];
                        end
                        3'b100: ;
                        3'b101: ;
                        3'b110: ;
                        3'b111: ;
                    endcase
                    pc <= pc + 4;
                end
                7'b1100111: begin
                    case (func3)
                        //TODO add rd, when i find out what it does
                        3'b000: pc <= registers[rs1] + 64'(imm);
                        3'b001: ;
                        3'b010: ;
                        3'b011: ;
                        3'b100: ;
                        3'b101: ;
                        3'b110: ;
                        3'b111: ;
                    endcase
                end
                default: pc <= pc + 4;
            endcase
        end
    end

endmodule
