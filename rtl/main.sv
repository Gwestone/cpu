import cpu_types::*;
import load_types::*;

typedef struct packed {
    logic [6:0] func7;
    logic [4:0] rs2;
    logic [4:0] rs1;
    logic [2:0] func3;
    logic [4:0] rd;
    logic [6:0] opcode;
} instruction_t;

module main(
    input  wire        clk,
    input  wire        reset,
    output wire [63:0] raddr,
    input  wire [63:0] rdata,
    output logic  [63:0] waddr,
    output logic  [63:0] wdata,
    output logic         wen
);
    logic [63:0] pc;
    logic [63:0] registers [32];
    logic[63:0] load_addr;
    logic[4:0]  load_reg;
    load_func_t load_func;

    logic [63:0] write_addr;
    logic [4:0] write_reg;
    logic [63:0] write_stecil;

    cpu_state_t  state;
    logic [31:0] instruction_reg;

    // Combinational decode — valid only when state == EXEC and rdata holds an instruction
    logic [6:0] opcode;
    logic [2:0] func3;
    logic [6:0] func7;
    logic [4:0] rs1;
    logic [4:0] rs2;
    logic [4:0] rd;

    // assign opcode = instruction_reg[6:0];
    // assign rd = instruction_reg[10:7];
    // assign func3 = instruction_reg[14:11];
    // assign rs1 = instruction_reg[19:15];
    // assign rs2 = instruction_reg[24:20];
    // assign func7 = instruction_reg[31:25];

    wire instruction_t inst = instruction_reg;

    logic [63:0] alu_a;
    logic [63:0] alu_b;

    assign alu_a = registers[inst.rs1];

    alu_b_decoder alu_b_dec(
        .opcode(inst.opcode),
        .rdata(instruction_reg),
        .rs_reg(registers[inst.rs2]),
        .alu_b(alu_b)
    );

    logic [63:0] alu_mask;

    alu_mask_decoder alu_mask_dec(
        .opcode(inst.opcode),
        .func3(inst.func3),
        .func7(inst.func7),
        .alu_mask(alu_mask)
    );

    logic [3:0]  alu_op;
    logic [63:0] alu_result;

    alu_controller alu_ctrl(
        .opcode(inst.opcode),
        .func3(inst.func3),
        .func7(inst.func7),
        .alu_op(alu_op)
    );

    alu alu_inst(
        .a_in(alu_a),
        .b_in(alu_b),
        .mask_in(alu_mask),
        .alu_op_in(alu_op),
        .result_out(alu_result)
    );

    // raddr: point at instruction during FETCH_INSTRUCTION, data during load states
    assign raddr = (state == LOAD_WAIT || state == LOAD_DONE) ? load_addr : pc;

    assign waddr = (state == SEND_WAIT || state == SEND_DONE) ? write_addr : {64{1'b0}};
    assign wen = (state == SEND_DONE);

    always_ff @(posedge clk) begin
        if (reset) begin
            pc         <= 0;
            load_addr  <= 0;
            load_reg   <= 0;
            wdata      <= 0;
            state      <= FETCH_ADDR;
            load_func  <= LDU;
            for (integer i = 0; i < 32; i = i + 1)
                registers[i] <= 0;

        end else begin
            case (state)

                FETCH_ADDR: begin
                    state <= FETCH_INSTRUCTION;
                end

                FETCH_INSTRUCTION: begin
                    instruction_reg <= rdata[31:0];
                    state <= EXEC;
                end

                EXEC: begin
                    unique case (inst.opcode)

                        OP_LUI: begin           // U-type (lui)
                            if (inst.rd != 0)
                                registers[inst.rd] <= alu_result;
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        OP_AUIPC: begin           // U-type (auipc)
                            if (inst.rd != 0)
                                registers[inst.rd] <= pc + alu_result;
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        OP_JAL: begin           // J-type (jal)
                            if (inst.rd != 0)
                                registers[inst.rd] <= pc + 4;
                            pc <= pc + alu_result;
                            state <= FETCH_ADDR;
                        end

                        OP_JALR: begin           // jalr
                            case (inst.func3)
                                3'b000: begin
                                    if (inst.rd != 0)
                                        registers[inst.rd] <= pc + 4;
                                    pc <= alu_result;
                                    state <= FETCH_ADDR;
                                end
                                default: begin
                                    $fatal(1, "Illegal jalr opcode 0x%h at pc 0x%h", opcode, pc);
                                end
                            endcase
                        end

                        OP_BRANCH: begin           // B-type (branch)
                                if(inst.func3 == 3'b000) begin          // BEQ
                                    if (registers[inst.rs1] == registers[inst.rs2])
                                        pc <= pc + alu_result;
                                end
                                else if(inst.func3 == 3'b001) begin     // BNE
                                    if (registers[inst.rs1] != registers[inst.rs2])
                                        pc <= pc + alu_result;
                                end
                                else if(inst.func3 == 3'b100) begin     // BLT
                                    if ($signed(registers[inst.rs1]) < $signed(registers[inst.rs2]))
                                        pc <= pc + alu_result;
                                end
                                else if(inst.func3 == 3'b101) begin     // BGE
                                    if ($signed(registers[inst.rs1]) >= $signed(registers[inst.rs2]))
                                        pc <= pc + alu_result;
                                end
                                else if(inst.func3 == 3'b110) begin     // BLTU
                                    if ($unsigned(registers[inst.rs1]) < $unsigned(registers[inst.rs2]))
                                        pc <= pc + alu_result;
                                end
                                else if(inst.func3 == 3'b111) begin     // BGEU
                                    if ($unsigned(registers[inst.rs1]) >= $unsigned(registers[inst.rs2]))
                                        pc <= pc + alu_result;
                                end
                                else begin
                                    $error("Unsupported branch instruction: opcode=%b func3=%b func7=%b", inst.opcode, inst.func3, inst.func7);
                                end
                                state <= FETCH_ADDR;
                        end

                        OP_LOAD: begin           // Load opcode
                            case (inst.func3)
                                3'b000: begin       // lb
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LB;
                                end
                                3'b100: begin       // lbu
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LBU;
                                end
                                3'b001: begin       // lh
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LH;
                                end
                                3'b101: begin       // lhu
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LHU;
                                end
                                3'b010: begin       // lw
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LW;
                                end
                                3'b110: begin       // lwu
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LWU;
                                end
                                3'b011: begin       // ld
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LD;
                                end
                                3'b111: begin       // ldu
                                    load_addr <= alu_result;
                                    load_reg  <= inst.rd;
                                    load_func <= LDU;
                                end
                                default: begin
                                    $error("Unsupported load func3: %b", inst.func3);
                                end
                            endcase
                            state <= LOAD_WAIT;
                            pc <= pc + 4;
                        end

                        OP_STORE: begin             // S-type store
                            //TODO add write strobes latelly and make multistage
                            case (inst.func3)
                                3'b000: begin       // sb
                                    write_addr <= alu_result;
                                    write_reg <= inst.rs2;
                                    write_stecil <= {{56{1'b1}}, 8'hff};
                                end
                                3'b001: begin       // sh
                                    write_addr <= alu_result;
                                    write_reg <= inst.rs2;
                                    write_stecil <= {{48{1'b1}}, 16'hffff};
                                end
                                3'b010: begin       // sw
                                    write_addr <= alu_result;
                                    write_reg <= inst.rs2;
                                    write_stecil <= {{32{1'b1}}, 32'hffffffff};
                                end
                                3'b011: begin       // sd
                                    write_addr <= alu_result;
                                    write_reg <= inst.rs2;
                                    write_stecil <= {64{1'b1}};
                                end
                                default: ;
                            endcase
                            pc <= pc + 4;
                            //implement WRITE_WAIT
                            state <= SEND_WAIT;
                        end

                        OP_IMM: begin           // I-type arithmetic
                            if (inst.rd != 0) begin
                                //TODO implement the separate alu_mask_decoder for input and output
                                if (inst.func3 == 3'b000) begin       // addi
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b010) begin       // slti
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b011) begin       // sltiu
                                    registers[inst.rd] <= alu_result;
                                end else if (inst.func3 == 3'b100) begin       // xori
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b110) begin       // ori
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b111) begin       // andi
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b001 && inst.func7 == 7'b0000000) begin // slli
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b101 && inst.func7 == 7'b0000000) begin // srli
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end else if (inst.func3 == 3'b101 && inst.func7 == 7'b0100000) begin // srai
                                    registers[inst.rd] <= {{32{alu_result[31]}}, alu_result[31:0]};
                                end
                            end
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        OP_REG: begin   //register instructions
                            if (inst.func3 == 3'b000 && inst.func7 == 7'b0) begin   // add
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b000 && inst.func7 == 7'b0100000) begin   // sub
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b001 && inst.func7 == 7'b0000000) begin   // sll
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b010 && inst.func7 == 7'b0000000) begin   // slt
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b011 && inst.func7 == 7'b0000000) begin   // sltu
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b100 && inst.func7 == 7'b0000000) begin   // xor
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            //TODO implement logical shift
                            else if (inst.func3 == 3'b101 && inst.func7 == 7'b0000000) begin   // srl
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b101 && inst.func7 == 7'b0100000) begin   // sra
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b110 && inst.func7 == 7'b0000000) begin   // or
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            else if (inst.func3 == 3'b111 && inst.func7 == 7'b0000000) begin   // and
                                if (inst.rd != 0)
                                    registers[inst.rd] <= alu_result;
                            end
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end
                        // not in RV32I
                        OP_REG_W: begin
                            if (inst.rd != 0) begin
                                if (inst.func3 == 3'b000 && inst.func7 == 7'b0000000) begin // addw
                                    registers[inst.rd] <= alu_result;
                                end else if (inst.func3 == 3'b000 && inst.func7 == 7'b0100000) begin // subw
                                    registers[inst.rd] <= alu_result;
                                end else if (inst.func3 == 3'b001 && inst.func7 == 7'b0000000) begin // sllw
                                    registers[inst.rd] <= alu_result;
                                end else if (inst.func3 == 3'b101 && inst.func7 == 7'b0000000) begin // srlw
                                    registers[inst.rd] <= alu_result;
                                end else if (inst.func3 == 3'b101 && inst.func7 == 7'b0100000) begin // sraw
                                    registers[inst.rd] <= alu_result;
                                end
                            end
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        default: begin
                            pc <= pc + 4;      // NOP / unknown — skip
                            state <= FETCH_ADDR;
                        end
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
                    if (load_reg != 0)
                        case (load_func)
                            LB: registers[load_reg] <= {{56{rdata[7]}},  rdata[7:0]};
                            LH: registers[load_reg] <= {{48{rdata[15]}}, rdata[15:0]};
                            LW: registers[load_reg] <= {{32{rdata[31]}}, rdata[31:0]};
                            LD: registers[load_reg] <= rdata;
                            LBU: registers[load_reg] <= {56'b0, rdata[7:0]};
                            LHU: registers[load_reg] <= {48'b0, rdata[15:0]};
                            LWU: registers[load_reg] <= {32'b0, rdata[31:0]};
                            LDU: registers[load_reg] <= rdata;
                            default: registers[load_reg] <= rdata;
                        endcase
                    load_reg <= 0;
                    load_addr <= 0;
                    state    <= FETCH_ADDR;
                    load_func <= LDU;
                end

                SEND_WAIT: begin
                    // waddr == load_addr is stable this cycle.
                    // Async memory: wdata already valid — could capture here.
                    // Sync memory:  wdata valid NEXT cycle — must wait.
                    // LOAD_DONE handles both cases safely.
                    wdata <= registers[write_reg] & write_stecil;
                    state <= SEND_DONE;
                end

                SEND_DONE: begin
                    wdata <= 0;
                    write_addr <= 0;
                    write_reg <= 0;
                    write_stecil <= 0;
                    state <= FETCH_ADDR;
                end

                default: state <= EXEC;             // unreachable, but safe
            endcase
        end
    end
endmodule
