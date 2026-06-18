from cocotb.triggers import ClockCycles

from tests.isa import ISA

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
