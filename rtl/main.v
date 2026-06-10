module main(
    input  wire        clk,
    input  wire        reset,
    output wire [63:0] raddr,
    input  wire [63:0] rdata,
    output reg  [63:0] waddr,
    output reg  [63:0] wdata
);

    // State encoding — named constants, no magic numbers
    localparam EXEC      = 2'b00;
    localparam LOAD_WAIT = 2'b01;  // address on bus, waiting for memory
    localparam LOAD_DONE = 2'b10;  // rdata is valid, capture it

    reg [63:0] pc;
    reg [63:0] registers [0:31];
    reg [63:0] load_addr;
    reg [4:0]  load_reg;
    reg [1:0]  state;

    // Combinational decode — valid only when state == EXEC and rdata holds an instruction
    wire [6:0]  opcode = rdata[6:0];
    wire [2:0]  func3  = rdata[14:12];
    wire [6:0]  func7  = rdata[31:25];
    wire [4:0]  rs1    = rdata[19:15];
    wire [4:0]  rs2    = rdata[24:20];
    wire [4:0]  rd     = rdata[11:7];

    wire [63:0] imm_i  = {{52{rdata[31]}}, rdata[31:20]};
    wire [63:0] imm_s  = {{52{rdata[31]}}, rdata[31:25], rdata[11:7]};
    wire [63:0] imm_b = {{51{rdata[31]}}, rdata[31], rdata[7], rdata[30:25], rdata[11:8], 1'b0};
    wire [63:0] imm_j = {{43{rdata[31]}}, rdata[31], rdata[19:12], rdata[20], rdata[30:21], 1'b0};
    wire [63:0] imm_u = {{32{rdata[31]}}, rdata[31:12], 12'b0};

    wire [63:0] alu_a = registers[rs1];

    wire [63:0] alu_b =
        (opcode == 7'b0010011) ? imm_i :   // I-type arithmetic (addi etc)
        (opcode == 7'b0000011) ? imm_i :   // loads
        (opcode == 7'b1100111) ? imm_i :   // jalr
        (opcode == 7'b0100011) ? imm_s :   // stores
        (opcode == 7'b1100011) ? imm_b :   // branches
        (opcode == 7'b1101111) ? imm_j :   // jal
        (opcode == 7'b0110111) ? imm_u :   // lui
        (opcode == 7'b0010111) ? imm_u :   // auipc
        registers[rs2];                    // R-type default

    wire [3:0]  alu_op;
    wire [63:0] alu_result;

    alu_controller alu_ctrl(
        .opcode(opcode),
        .func3(func3),
        .func7(func7),
        .alu_op(alu_op)
    );

    alu alu_inst(
        .a(alu_a),
        .b(alu_b),
        .alu_op(alu_op),
        .result(alu_result)
    );

    // raddr: point at instruction during EXEC, data during load states
    assign raddr = (state == EXEC) ? pc : load_addr;

    always @(posedge clk) begin
        if (reset) begin
            pc         <= 0;
            load_addr  <= 0;
            load_reg   <= 0;
            waddr      <= 0;
            wdata      <= 0;
            state      <= EXEC;
            for (integer i = 0; i < 32; i = i + 1)
                registers[i] <= 0;

        end else begin
            case (state)

                EXEC: begin
                    case (opcode)
                        7'b0010011: begin           // I-type arithmetic
                            case (func3)
                                3'b000: begin       // addi
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b001: begin       // subi
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b010: begin       // andi
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b011: begin       // ori
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b100: begin       // xori
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b101: begin       // slli
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end
                                3'b110: begin       // srli
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                end

                                default: ;
                            endcase
                            pc <= pc + 4;
                        end

                        7'b0000011: begin           // Load
                            case (func3)
                                3'b000: begin       // lb
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                end
                                default: pc <= pc + 4;
                            endcase
                        end

                        7'b0100011: begin           // S-type store
                            case (func3)
                                3'b011: begin       // sd
                                    waddr <= registers[rs1] + imm_s;
                                    wdata <= registers[rs2];
                                end
                                default: ;
                            endcase
                            pc <= pc + 4;
                        end

                        7'b1100111: begin           // jalr
                            case (func3)
                                3'b000: begin
                                    if (rd != 0)
                                        registers[rd] <= pc + 4;
                                    pc <= alu_result;
                                end
                                default: pc <= pc + 4;
                            endcase
                        end

                        default: pc <= pc + 4;      // NOP / unknown — skip
                    endcase
                end

                LOAD_WAIT: begin
                    // raddr == load_addr is stable this cycle.
                    // Async memory: rdata already valid — could capture here.
                    // Sync memory:  rdata valid NEXT cycle — must wait.
                    // LOAD_DONE handles both cases safely.
                    state <= LOAD_DONE;
                end

                LOAD_DONE: begin
                    // rdata is guaranteed valid for load_addr regardless of memory type
                    // TODO add flag to know size of data to read, also add same states to write data into memory
                    if (load_reg != 0)
                        registers[load_reg] <= rdata; // lb: sign-extend byte
                    load_reg <= 0;
                    load_addr <= 0;
                    state    <= EXEC;
                end

                default: state <= EXEC;             // unreachable, but safe
            endcase
        end
    end
endmodule
