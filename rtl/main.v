module main(
    input  wire        clk,
    input  wire        reset,
    output wire [63:0] raddr,
    input  wire [63:0] rdata,
    output reg  [63:0] waddr,
    output reg  [63:0] wdata
);

    // State encoding — named constants, no magic numbers
    localparam FETCH_ADDR = 3'b000;  // latching address from pc into raddr
    localparam FETCH_INSTRUCTION = 3'b001;  // latching instruction from memory into instruction_register
    localparam EXEC      = 3'b010;  // executing instruction
    localparam LOAD_WAIT = 3'b011;  // address on bus, waiting for memory
    localparam LOAD_DONE = 3'b100;  // rdata is valid, capture it

    reg [63:0] pc;
    reg [63:0] registers [0:31];
    reg [63:0] load_addr;
    reg [4:0]  load_reg;
    reg [63:0] load_mask;
    reg [2:0]  state;
    reg [31:0] instruction_reg;

    // Combinational decode — valid only when state == EXEC and rdata holds an instruction
    wire [6:0]  opcode = instruction_reg[6:0];
    wire [2:0]  func3  = instruction_reg[14:12];
    wire [6:0]  func7  = instruction_reg[31:25];
    wire [4:0]  rs1    = instruction_reg[19:15];
    wire [4:0]  rs2    = instruction_reg[24:20];
    wire [4:0]  rd     = instruction_reg[11:7];

    wire [63:0] alu_a = registers[rs1];
    wire [63:0] alu_b;

    alu_b_decoder alu_b_dec(
        .opcode(opcode),
        .rdata(instruction_reg),
        .rs_reg(registers[rs2]),
        .alu_b(alu_b)
    );

    wire [63:0] alu_mask;

    alu_mask_decoder alu_mask_dec(
        .opcode(opcode),
        .func3(func3),
        .func7(func7),
        .alu_mask(alu_mask)
    );

    wire [3:0]  alu_op;
    wire [63:0] alu_result;

    alu_controller alu_ctrl(
        .opcode(opcode),
        .func3(func3),
        .func7(func7),
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

    always @(posedge clk) begin
        if (reset) begin
            pc         <= 0;
            load_addr  <= 0;
            load_reg   <= 0;
            waddr      <= 0;
            wdata      <= 0;
            state      <= FETCH_ADDR;
            load_mask  <= {64{1'b1}};
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
                    case (opcode)
                        7'b0011011: begin           // addiw I-type arithmetic
                            if (rd != 0) begin
                                if (func3 == 3'b000) begin       // addiw
                                    registers[rd] <= {{32{alu_result[31]}}, alu_result[31:0]}; // cast to 32 bits signed
                                end else if (func3 == 3'b001) begin       // slliw
                                    registers[rd] <= {{32{alu_result[31]}}, alu_result[31:0]}; // shift 32 bits left
                                end else if (func3 == 3'b101 && func7 == 7'b0000000) begin       // srliw
                                    registers[rd] <= {{32{alu_result[31]}}, alu_result[31:0]}; // shift 32 bits left
                                end else if (func3 == 3'b101 && func7 == 7'b0100000) begin       // sraiw
                                    registers[rd] <= {{32{alu_result[31]}}, alu_result[31:0]}; // shift 32 bits left
                                end
                            end
                            pc <= pc + 4;
                            state <= FETCH_INSTRUCTION;
                        end

                        7'b0111011: begin
                            if (rd != 0) begin
                                if (func3 == 3'b000 && func7 == 7'b0000000) begin       // addw
                                    registers[rd] <= alu_result;
                                end else if (func3 == 3'b000 && func7 == 7'b0100000) begin       // subw
                                    registers[rd] <= alu_result;
                                end else if (func3 == 3'b001 && func7 == 7'b0000000) begin       // sllw
                                    registers[rd] <= alu_result;
                                end else if (func3 == 3'b101 && func7 == 7'b0000000) begin       // srlw
                                    registers[rd] <= alu_result;
                                end else if (func3 == 3'b101 && func7 == 7'b0100000) begin       // sraw
                                    registers[rd] <= alu_result;
                                end

                            end
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        7'b0110111: begin           // U-type (lui)
                            if (rd != 0)
                                registers[rd] <= alu_result;
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        7'b0010111: begin           // U-type (auipc)
                            if (rd != 0)
                                registers[rd] <= pc + alu_result;
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        7'b0010011: begin           // I-type arithmetic (addi)
                            case(func3)
                                3'b000: begin       // addi
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                //TODO rewrite all using func7 to use switch
                                3'b001: begin       // slli
                                    if(func7 == 7'b0000000)begin
                                        if (rd != 0)
                                            registers[rd] <= alu_result;
                                        pc <= pc + 4;
                                        state <= FETCH_ADDR;
                                    end
                                end
                                3'b101: begin
                                    case(func7)
                                        7'b0000000: begin   // srli
                                            if (rd != 0)
                                                registers[rd] <= alu_result;
                                            pc <= pc + 4;
                                            state <= FETCH_ADDR;
                                        end
                                        7'b0100000: begin   // srai
                                            if (rd != 0)
                                                registers[rd] <= alu_result;
                                            pc <= pc + 4;
                                            state <= FETCH_ADDR;
                                        end
                                        default: begin
                                            if (rd != 0)
                                                registers[rd] <= alu_result;
                                            pc <= pc + 4;
                                            state <= FETCH_ADDR;
                                        end
                                    endcase
                                end
                                3'b010: begin       // slti
                                    if ($signed(registers[rs1]) < $signed(alu_result) && rd != 0)
                                        registers[rd] <= 1;
                                    else if (rd != 0)
                                        registers[rd] <= 0;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b011: begin       // sltiu
                                    if ($unsigned(registers[rs1]) < $unsigned(alu_result) && rd != 0)
                                        registers[rd] <= 1;
                                    else if (rd != 0)
                                        registers[rd] <= 0;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b100: begin       // xori
                                    if(rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b110: begin       // ori
                                    if(rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b111: begin       // andi
                                    if(rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                            endcase
                        end

                        7'b0000011: begin           // Load opcode
                            case (func3)
                            //TODO add sign extension
                                3'b000: begin       // lb
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {56'b0, {8{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b100: begin       // lbu
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {56'b0, {8{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b001: begin       // lh
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {48'b0, {16{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b101: begin       // lhu
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {48'b0, {16{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b010: begin       // lw
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {32'b0, {32{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b110: begin       // lwu
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {32'b0, {32{1'b1}}};
                                    pc <= pc + 4;
                                end
                                3'b011: begin       // ld
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {64{1'b1}};
                                    pc <= pc + 4;
                                end
                                3'b111: begin       // ldu
                                    //address to load from
                                    load_addr <= alu_result;
                                    load_reg  <= rd;
                                    state     <= LOAD_WAIT;
                                    load_mask <= {64{1'b1}};
                                    pc <= pc + 4;
                                end
                                default: begin
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                            endcase
                        end

                        7'b0100011: begin           // S-type store
                            //TODO write separate states for store like it is done for load
                            case (func3)
                                3'b000: begin       // sb
                                    waddr <= alu_result;
                                    wdata <= registers[rs2];
                                end
                                3'b001: begin       // sh
                                    waddr <= alu_result;
                                    wdata <= registers[rs2];
                                end
                                3'b010: begin       // sw
                                    waddr <= alu_result;
                                    wdata <= registers[rs2];
                                end
                                3'b011: begin       // sd
                                    waddr <= alu_result;
                                    wdata <= registers[rs2];
                                end
                                default: ;
                            endcase
                            pc <= pc + 4;
                            state <= FETCH_ADDR;
                        end

                        7'b1101111: begin           // J-type (jal)
                            if (rd != 0)
                                registers[rd] <= pc + 4;
                            pc <= pc + alu_result;
                            state <= FETCH_ADDR;
                        end

                        7'b1100111: begin           // jalr
                            case (func3)
                                3'b000: begin
                                    if (rd != 0)
                                        registers[rd] <= pc + 4;
                                    pc <= alu_result;
                                    state <= FETCH_ADDR;
                                end
                                default: begin
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                            endcase
                        end

                        7'b1100011: begin           // B-type (branch)
                            case (func3)
                                3'b000: begin       // BEQ
                                    if (registers[rs1] == registers[rs2])
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b001: begin       // BNE
                                    if (registers[rs1] != registers[rs2])
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b100: begin       // BLT
                                    if ($signed(registers[rs1]) < $signed(registers[rs2]))
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b101: begin       // BGE
                                    if ($signed(registers[rs1]) > $signed(registers[rs2]))
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b110: begin       // BLTU
                                    if ($unsigned(registers[rs1]) > $unsigned(registers[rs2]))
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                3'b111: begin       // BGEU
                                    if ($unsigned(registers[rs1]) >= $unsigned(registers[rs2]))
                                        pc <= pc + alu_result;
                                    else
                                        pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                default: begin
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                            endcase
                        end

                        7'b0110011: begin   //add instructions
                            case({func3, func7})
                                {3'b000, 7'b0}: begin   // add
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b000, 7'b0100000}: begin   // sub
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b001, 7'b0000000}: begin   // sll
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b010, 7'b0000000}: begin   // slt
                                    if ($signed(registers[rs1]) < $signed(registers[rs2]) && rd != 0)
                                        registers[rd] <= 1;
                                    else if (rd != 0)
                                        registers[rd] <= 0;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b011, 7'b0000000}: begin   // sltu
                                    if ($unsigned(registers[rs1]) < $unsigned(registers[rs2]) && rd != 0)
                                        registers[rd] <= 1;
                                    else if (rd != 0)
                                        registers[rd] <= 0;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b100, 7'b0000000}: begin   // xor
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                //TODO implement logical shift
                                {3'b101, 7'b0000000}: begin   // srl
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b101, 7'b0100000}: begin   // srl
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b110, 7'b0000000}: begin   // or
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                                {3'b111, 7'b0100000}: begin   // and
                                    if (rd != 0)
                                        registers[rd] <= alu_result;
                                    pc <= pc + 4;
                                    state <= FETCH_ADDR;
                                end
                            endcase
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
                    // TODO add flag to know size of data to read, also add same states to write data into memory
                    if (load_reg != 0)
                        registers[load_reg] <= rdata & load_mask; // lb: sign-extend byte //TODO do i really need to sight extend it?
                    load_reg <= 0;
                    load_addr <= 0;
                    state    <= FETCH_ADDR;
                    load_mask <= {64{1'b1}};
                end

                default: state <= EXEC;             // unreachable, but safe
            endcase
        end
    end
endmodule
