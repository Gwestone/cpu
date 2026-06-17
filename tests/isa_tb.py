import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from .isa import ISA

r = ISA.reg


# ─────────────────────────────────────────────────────────────────────────
# Memory helpers
# ─────────────────────────────────────────────────────────────────────────
def read_memory(address, array):
    if address + 4 > len(array):
        return 0
    return (
        array[address]
        | (array[address + 1] << 8)
        | (array[address + 2] << 16)
        | (array[address + 3] << 24)
    )


def write_memory(address, wen, data, array):
    # only write when write-enable asserted and address in range
    if wen != 1:
        return
    if address == 0xFFFFFFFFFFFFFFFF:
        return
    if address + 8 > len(array):
        return
    for i in range(8):
        array[address + i] = (data >> (i * 8)) & 0xFF


async def reset(dut):
    dut.reset.value = 1
    await ClockCycles(dut.clk, 1)
    dut.reset.value = 0
    await ClockCycles(dut.clk, 1)


# ─────────────────────────────────────────────────────────────────────────
# Test harness — builds a program, runs it until the trailing jalr loop,
# then returns so the caller can assert on register/memory state.
#
# Convention: every test program ends with a self-loop:
#     addi  t6, zero, <loop_addr>   # address of the jalr itself
#     jalr  zero, t6, 0             # jump to self forever
# The harness detects pc parked at loop_addr and stops.
# ─────────────────────────────────────────────────────────────────────────
async def run_program(dut, text_section, data_bytes=64, max_cycles=None, log=False):
    """Assemble text_section + zeroed data, run until the trailing jalr
    self-loop is reached (pc stops advancing), or until max_cycles."""
    await reset(dut)

    program = bytearray()
    program.extend(ISA.make_blob(text_section))
    program.extend(ISA.make_blob([0x00] * data_bytes))

    # address of the last instruction (the jalr loop)
    loop_addr = (len(text_section) - 1) * 4

    if max_cycles is None:
        max_cycles = len(text_section) * 12

    last_pc = -1
    stable_count = 0

    for cycle in range(max_cycles):
        addr = int(dut.raddr.value)
        data = read_memory(addr, program)
        write_memory(
            int(dut.waddr.value),
            int(dut.wen.value),
            int(dut.wdata.value),
            program,
        )
        dut.rdata.value = data

        if log:
            inst_val = int(dut.instruction_reg.value)
            dut._log.info(
                f"cycle={cycle:>3}"
                f"  state={int(dut.state.value)}"
                f"  pc={hex(int(dut.pc.value))}"
                f"  instr={hex(inst_val)}"
                f"  opcode={inst_val & 0x7F:#04x}"
            )

        await ClockCycles(dut.clk, 1)

        # detect the self-loop: pc parked at loop_addr for a few cycles
        cur_pc = int(dut.pc.value)
        if cur_pc == loop_addr and cur_pc == last_pc:
            stable_count += 1
            if stable_count >= 3:
                if log:
                    dut._log.info(f"loop reached at pc={hex(cur_pc)}, stopping")
                break
        else:
            stable_count = 0
        last_pc = cur_pc

    return program


def reg(dut, name):
    """Read a register as a signed 64-bit value."""
    val = int(dut.registers[name].value)
    if val & (1 << 63):
        val -= 1 << 64
    return val


def regu(dut, name):
    """Read a register as an unsigned 64-bit value."""
    return int(dut.registers[name].value)


def loop_tail(loop_reg=r.t6):
    """Return the two-instruction self-loop tail.
    Must be appended to every test program."""
    # placeholder address filled by caller via make_program
    return None


def make_program(body):
    """Append a self-loop tail to the instruction body.
    The jalr jumps to its own address, parking the pc."""
    prog = list(body)
    loop_idx = len(prog) + 1  # index of the jalr (after the addi)
    loop_addr = loop_idx * 4
    prog.append(ISA.addi(r.t6, r.zero, loop_addr))  # t6 = address of jalr
    prog.append(ISA.jalr(r.zero, r.t6, 0))  # jump to self
    return prog


# ═════════════════════════════════════════════════════════════════════════
# I-TYPE ARITHMETIC
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_addi(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.a0, 10),
            ISA.addi(r.a2, r.a0, -3),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a0) == 5, f"a0={reg(dut, r.a0)}"
    assert reg(dut, r.a1) == 15, f"a1={reg(dut, r.a1)}"
    assert reg(dut, r.a2) == 2, f"a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_slti(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.slti(r.a1, r.a0, 10),  # 5 < 10 → 1
            ISA.slti(r.a2, r.a0, 3),  # 5 < 3 → 0
            ISA.addi(r.a3, r.zero, -1),
            ISA.slti(r.a4, r.a3, 0),  # -1 < 0 → 1 (signed)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 1, f"slti 5<10 a1={reg(dut, r.a1)}"
    assert reg(dut, r.a2) == 0, f"slti 5<3 a2={reg(dut, r.a2)}"
    assert reg(dut, r.a4) == 1, f"slti -1<0 a4={reg(dut, r.a4)}"


@cocotb.test()
async def test_sltiu(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.sltiu(r.a1, r.a0, 10),  # 5 < 10 → 1
            ISA.addi(r.a2, r.zero, -1),  # 0xFFFF...FF (huge unsigned)
            ISA.sltiu(r.a3, r.a0, -1),  # 5 < huge → 1
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 1, f"sltiu 5<10 a1={reg(dut, r.a1)}"
    assert reg(dut, r.a3) == 1, f"sltiu 5<huge a3={reg(dut, r.a3)}"


@cocotb.test()
async def test_xori(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0xF),
            ISA.xori(r.a1, r.a0, 0x3),  # 0xF ^ 0x3 = 0xC
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 0xC, f"xori a1={hex(reg(dut, r.a1))}"


@cocotb.test()
async def test_ori(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x8),
            ISA.ori(r.a1, r.a0, 0x3),  # 0x8 | 0x3 = 0xB
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 0xB, f"ori a1={hex(reg(dut, r.a1))}"


@cocotb.test()
async def test_andi(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0xF),
            ISA.andi(r.a1, r.a0, 0x9),  # 0xF & 0x9 = 0x9
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 0x9, f"andi a1={hex(reg(dut, r.a1))}"


@cocotb.test()
async def test_slli(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a1, r.a0, 4),  # 1 << 4 = 16
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 16, f"slli a1={reg(dut, r.a1)}"


@cocotb.test()
async def test_srli(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 256),
            ISA.srli(r.a1, r.a0, 4),  # 256 >> 4 = 16
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 16, f"srli a1={reg(dut, r.a1)}"


@cocotb.test()
async def test_srai(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -16),
            ISA.srai(r.a1, r.a0, 2),  # -16 >> 2 = -4 (arithmetic)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == -4, f"srai a1={reg(dut, r.a1)}"


# ═════════════════════════════════════════════════════════════════════════
# R-TYPE ARITHMETIC
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_add(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 7),
            ISA.addi(r.a1, r.zero, 11),
            ISA.add(r.a2, r.a0, r.a1),  # 7 + 11 = 18
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 18, f"add a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sub(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 20),
            ISA.addi(r.a1, r.zero, 8),
            ISA.sub(r.a2, r.a0, r.a1),  # 20 - 8 = 12
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 12, f"sub a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sll(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 3),
            ISA.addi(r.a1, r.zero, 4),
            ISA.sll(r.a2, r.a0, r.a1),  # 3 << 4 = 48
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 48, f"sll a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_slt(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -5),
            ISA.addi(r.a1, r.zero, 3),
            ISA.slt(r.a2, r.a0, r.a1),  # -5 < 3 → 1 (signed)
            ISA.slt(r.a3, r.a1, r.a0),  # 3 < -5 → 0
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 1, f"slt a2={reg(dut, r.a2)}"
    assert reg(dut, r.a3) == 0, f"slt a3={reg(dut, r.a3)}"


@cocotb.test()
async def test_sltu(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -1),  # huge unsigned
            ISA.addi(r.a1, r.zero, 1),
            ISA.sltu(r.a2, r.a1, r.a0),  # 1 < huge → 1
            ISA.sltu(r.a3, r.a0, r.a1),  # huge < 1 → 0
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 1, f"sltu a2={reg(dut, r.a2)}"
    assert reg(dut, r.a3) == 0, f"sltu a3={reg(dut, r.a3)}"


@cocotb.test()
async def test_xor(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0xF),
            ISA.addi(r.a1, r.zero, 0x9),
            ISA.xor(r.a2, r.a0, r.a1),  # 0xF ^ 0x9 = 0x6
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0x6, f"xor a2={hex(reg(dut, r.a2))}"


@cocotb.test()
async def test_srl(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 256),
            ISA.addi(r.a1, r.zero, 4),
            ISA.srl(r.a2, r.a0, r.a1),  # 256 >> 4 = 16
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 16, f"srl a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sra(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -32),
            ISA.addi(r.a1, r.zero, 2),
            ISA.sra(r.a2, r.a0, r.a1),  # -32 >> 2 = -8 (arithmetic)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -8, f"sra a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_or(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x8),
            ISA.addi(r.a1, r.zero, 0x3),
            ISA.or_(r.a2, r.a0, r.a1),  # 0x8 | 0x3 = 0xB
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0xB, f"or a2={hex(reg(dut, r.a2))}"


@cocotb.test()
async def test_and(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0xF),
            ISA.addi(r.a1, r.zero, 0x9),
            ISA.and_(r.a2, r.a0, r.a1),  # 0xF & 0x9 = 0x9
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0x9, f"and a2={hex(reg(dut, r.a2))}"


# ═════════════════════════════════════════════════════════════════════════
# UPPER IMMEDIATE
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_lui(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.lui(r.a0, 0x12345),  # a0 = 0x12345 << 12 = 0x12345000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a0) == 0x12345000, f"lui a0={hex(regu(dut, r.a0))}"


@cocotb.test()
async def test_auipc(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # auipc at pc=0: a0 = 0 + (1 << 12) = 0x1000
    prog = make_program(
        [
            ISA.auipc(r.a0, 1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a0) == 0x1000, f"auipc a0={hex(regu(dut, r.a0))}"


# ═════════════════════════════════════════════════════════════════════════
# BRANCHES
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_beq_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # if equal, skip the "set a2=99" instruction
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.zero, 5),
            ISA.beq(r.a0, r.a1, 8),  # equal → skip next (branch +8)
            ISA.addi(r.a2, r.zero, 99),  # skipped if branch taken
            ISA.addi(r.a3, r.zero, 1),  # landing point
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"beq taken should skip, a2={reg(dut, r.a2)}"
    assert reg(dut, r.a3) == 1, f"a3={reg(dut, r.a3)}"


@cocotb.test()
async def test_bne_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.zero, 7),
            ISA.bne(r.a0, r.a1, 8),  # not equal → skip next
            ISA.addi(r.a2, r.zero, 99),  # skipped
            ISA.addi(r.a3, r.zero, 1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"bne taken should skip, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_blt_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -3),
            ISA.addi(r.a1, r.zero, 5),
            ISA.blt(r.a0, r.a1, 8),  # -3 < 5 → skip next
            ISA.addi(r.a2, r.zero, 99),  # skipped
            ISA.addi(r.a3, r.zero, 1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"blt taken should skip, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_bge_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.zero, 3),
            ISA.bge(r.a0, r.a1, 8),  # 5 >= 3 → skip next
            ISA.addi(r.a2, r.zero, 99),  # skipped
            ISA.addi(r.a3, r.zero, 1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"bge taken should skip, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_bltu_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.addi(r.a1, r.zero, -1),  # huge unsigned
            ISA.bltu(r.a0, r.a1, 8),  # 1 < huge → skip next
            ISA.addi(r.a2, r.zero, 99),  # skipped
            ISA.addi(r.a3, r.zero, 1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"bltu taken should skip, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_bgeu_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -1),  # huge unsigned
            ISA.addi(r.a1, r.zero, 1),
            ISA.bgeu(r.a0, r.a1, 8),  # huge >= 1 → skip next
            ISA.addi(r.a2, r.zero, 99),  # skipped
            ISA.addi(r.a3, r.zero, 1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"bgeu taken should skip, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_branch_not_taken(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # branch NOT taken → the "set a2=99" runs
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.zero, 7),
            ISA.beq(r.a0, r.a1, 8),  # 5 != 7 → NOT taken
            ISA.addi(r.a2, r.zero, 99),  # executed
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 99, (
        f"branch not taken, a2 should be 99 got {reg(dut, r.a2)}"
    )


# ═════════════════════════════════════════════════════════════════════════
# JUMPS
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_jal(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.jal(r.a0, 8),  # jump +8, save pc+4 in a0
            ISA.addi(r.a1, r.zero, 99),  # skipped
            ISA.addi(r.a2, r.zero, 1),  # landing
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 0, f"jal should skip, a1={reg(dut, r.a1)}"
    assert reg(dut, r.a0) == 4, f"jal return addr a0={reg(dut, r.a0)}"


# ═════════════════════════════════════════════════════════════════════════
# LOADS / STORES
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_sw_lw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),  # address (in data section)
            ISA.addi(r.a1, r.zero, 1234),  # value
            ISA.sw(r.a0, r.a1, 0),  # store word
            ISA.lw(r.a2, r.a0, 0),  # load word back
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 1234, f"sw/lw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sb_lb(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),
            ISA.addi(r.a1, r.zero, 0x7F),  # positive byte
            ISA.sb(r.a0, r.a1, 0),
            ISA.lb(r.a2, r.a0, 0),  # sign-extend
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0x7F, f"sb/lb a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_lb_sign_extend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),
            ISA.addi(r.a1, r.zero, 0xFF),  # -1 as a byte
            ISA.sb(r.a0, r.a1, 0),
            ISA.lb(r.a2, r.a0, 0),  # sign-extend → -1
            ISA.lbu(r.a3, r.a0, 0),  # zero-extend → 255
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -1, f"lb sign extend a2={reg(dut, r.a2)}"
    assert regu(dut, r.a3) == 255, f"lbu zero extend a3={regu(dut, r.a3)}"


# ═════════════════════════════════════════════════════════════════════════
# x0 BEHAVIOR
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_x0_stays_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.zero, r.zero, 42),  # writing x0 must have no effect
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.zero) == 0, f"x0 must stay 0, got {regu(dut, r.zero)}"
