module main(
    input  wire        clk,
    input  wire        reset,
    output reg  [63:0] raddr,
    input  wire [63:0] rdata,
    output reg  [63:0] waddr,
    output reg  [63:0] wdata
);
    reg [63:0] pc;
    reg [63:0] registers [0:31];

    // decode combinationally from rdata — no extra cycle
    wire [6:0]  opcode = rdata[6:0];
    wire [2:0]  func3  = rdata[14:12];
    wire [6:0]  func7  = rdata[31:25];
    wire [4:0]  rs1    = rdata[19:15];
    wire [4:0]  rs2    = rdata[24:20];
    wire [4:0]  rd     = rdata[11:7];

    // I-type immediate — sign extended to 64 bits
    wire [63:0] imm_i  = {{52{rdata[31]}}, rdata[31:20]};

    // S-type immediate — sign extended to 64 bits
    wire [63:0] imm_s  = {{52{rdata[31]}}, rdata[31:25], rdata[11:7]};

    always @(posedge clk) begin
        if (reset) begin
            pc <= 0;
            raddr <= 0;
            waddr <= 0;
            wdata <= 0;
            for (integer i = 0; i < 32; i = i + 1)
                registers[i] <= 0;
        end else begin
            raddr <= pc;   // fetch next PC
            case (opcode)
                7'b0000000: begin          // nop / unknown
                    pc <= pc + 4;
                end

                7'b0010011: begin          // I-type arithmetic
                    case (func3)
                        3'b000: begin      // addi
                            if (rd != 0)   // never write x0
                                registers[rd] <= registers[rs1] + imm_i;
                        end
                        default: ;
                    endcase
                    pc <= pc + 4;
                end

                7'b0100011: begin          // S-type store
                    case (func3)
                        3'b011: begin      // sd
                            waddr <= registers[rs1] + imm_s;
                            wdata <= registers[rs2];
                        end
                        default: ;
                    endcase
                    pc <= pc + 4;
                end

                7'b1100111: begin          // jalr
                    case (func3)
                        3'b000: begin
                            if (rd != 0)
                                registers[rd] <= pc + 4;  // save return addr
                            pc <= (registers[rs1] + imm_i) & ~64'h1;
                            // clear LSB as per RISC-V spec
                        end
                        default: ;
                    endcase
                end

                default: pc <= pc + 4;
            endcase
        end
    end
endmodule
