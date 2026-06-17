import copy
import struct
from os import getcwd, path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from .isa import ISA

r = ISA.reg

bin_file_path = path.join(getcwd(), "bin/src/firmware.bin")
bin_file = open(bin_file_path, "rb")
binary_blob = bin_file.read()


# TODO add read/write negotiation between CPU and memory controller
def read_memory(address, array):
    return (
        (array[address] << 0)  # first byte = least significant
        | (array[address + 1] << 8)
        | (array[address + 2] << 16)
        | (array[address + 3] << 24)  # last byte = most significant
    )


def write_memory(address, enable, data, array):
    if enable:
        array[address] = (data >> 0) & 0xFF
        array[address + 1] = (data >> 8) & 0xFF
        array[address + 2] = (data >> 16) & 0xFF
        array[address + 3] = (data >> 24) & 0xFF


def make_blob(words):
    blob = bytearray()
    for w in words:
        blob += struct.pack("<I", w)
    return blob


async def reset(dut):
    dut.reset.value = 1
    await ClockCycles(dut.clk, 1)
    dut.reset.value = 0
    await ClockCycles(dut.clk, 1)


@cocotb.test()
async def my_test(dut):
    """Try accessing the design."""
    cocotb.start_soon(Clock(dut.clk, 2).start())
    await reset(dut)

    blob_copy = copy.copy(binary_blob)
    # addi x0, x0, 0
    program = [0x00000013] * 40
    blob = make_blob(program)

    print("Entire program blob: " + " ".join(hex(i) for i in blob))
    for _ in range(10):
        address_to_read = dut.raddr.value
        print("Reading address: " + hex(address_to_read))
        dut.rdata.value = blob[address_to_read]
        await ClockCycles(dut.clk, 1)


@cocotb.test()
async def verify_isa_parser(dut):
    """Verify that the ISA parser correctly parses the program blob."""
    correct_program = [
        0x00000013,  # nop
        0x00210113,  # addi x2, x2, 2
        0x04008093,  # addi x1, x1, 64
        0x0020B023,  # sd x2, 0(x1)
        0x00000013,  # nop
        # end loop to prevent crash
        0x01800093,  # addi x1, x0, 24
        0x00008067,  # jalr x0, 0(x1) (infinite loop)
    ]

    tested_program = [
        ISA.nop(),  # nop
        ISA.addi(r.sp, r.sp, 2),  # addi x2, x2, 2
        ISA.addi(r.ra, r.ra, 64),  # addi x1, x1, 64
        ISA.sd(r.ra, r.sp, 0),  # sd x2, 0(x1)
        ISA.nop(),  # nop
        # end loop to prevent crash
        ISA.addi(r.ra, r.zero, 24),  # addi x1, x0, 24
        ISA.jalr(r.zero, r.ra, 0),  # jalr x0, 0(x1) (infinite loop)
    ]

    for counter in range(len(correct_program)):
        assert correct_program[counter] == tested_program[counter], (
            f"Expected {hex(correct_program[counter])}, got {hex(tested_program[counter])}"
        )


@cocotb.test()
async def immediate_add_operation(dut):
    """Try performing some computation and load some data from memory"""
    cocotb.start_soon(Clock(dut.clk, 2).start())
    await reset(dut)

    blob_copy = copy.copy(binary_blob)
    program = bytearray()

    text_section = [
        ISA.addi(r.a1, r.zero, 2),
        ISA.addi(r.a2, r.zero, 64),
        ISA.sd(r.a2, r.a1, 0),
        ISA.addi(r.a3, r.zero, 0),
        ISA.lb(r.a3, r.a2, 0),
        ISA.addi(r.a1, r.zero, 24),
        ISA.jalr(r.zero, r.a1, 0),
    ]

    text_blob = ISA.make_blob(text_section)
    program.extend(text_blob)

    data_section = [0x00] * 64
    data_blob = ISA.make_blob(data_section)
    program.extend(data_blob)

    dut._log.info("Program:")
    for i, w in enumerate(program):
        dut._log.info(f"  [{hex(i * 4)}] {hex(w)}")

    for cycle in range(len(text_section) * 10):
        addr = int(dut.raddr.value)
        data = read_memory(addr, program)
        write_memory(
            int(dut.waddr.value), int(dut.wen.value), int(dut.wdata.value), program
        )
        dut.rdata.value = data

        dut._log.info(
            f"cycle={cycle:>3}"
            f"  raddr={hex(addr):>6}"
            f"  rdata={hex(data):>12}"
            f"  state={int(dut.state.value)}"
            f"  pc={hex(int(dut.pc.value))}"
        )

        await ClockCycles(dut.clk, 1)

        # check if we've looped back — program complete
        if int(dut.pc.value) == 0x18 and cycle > 100:
            dut._log.info("Program completed — jalr loop detected")
            break

    # assert dut.waddr.value == 0x40
    # assert dut.wdata.value == 0x02

    # final assertions
    # int(dut.waddr.value) == 0x40, (
    #    f"waddr: expected 0x40 got {hex(int(dut.waddr.value))}"
    # )
    assert read_memory(0x40, program) == 0x02, (
        f"wdata: expected 0x02 got {hex(int(dut.wdata.value))}"
    )

    assert dut.registers[r.a3].value == 0x02


@cocotb.test()
async def loop_test(dut):
    """Test that the jalr loop is detected and pc wraps back to 0x18"""
    cocotb.start_soon(Clock(dut.clk, 2).start())
    await reset(dut)

    program = bytearray()

    text_section = [
        ISA.addi(r.a1, r.zero, 2),
        ISA.addi(r.a2, r.zero, 64),
        ISA.sd(r.a2, r.a1, 0),
        ISA.addi(r.a3, r.zero, 0),
        ISA.lb(r.a3, r.a2, 0),
        ISA.addi(r.a1, r.zero, 24),
        ISA.jalr(r.zero, r.a1, 0),
    ]

    text_blob = ISA.make_blob(text_section)
    program.extend(text_blob)

    data_section = [0x00] * 64
    data_blob = ISA.make_blob(data_section)
    program.extend(data_blob)

    dut._log.info("Program:")
    for i, w in enumerate(program):
        dut._log.info(f"  [{hex(i * 4)}] {hex(w)}")

    # run until jalr loops back (pc == 0x18) or timeout
    for cycle in range(len(text_section) * 10):
        # drive combinationally BEFORE edge
        addr = int(dut.raddr.value)
        data = read_memory(addr, program)
        write_memory(
            int(dut.waddr.value), int(dut.wen.value), int(dut.wdata.value), program
        )
        dut.rdata.value = data

        inst_val = int(dut.instruction_reg.value)
        opcode = inst_val & 0x7F  # bits [6:0]
        func3 = (inst_val >> 12) & 0x7  # bits [14:12]

        dut._log.info(
            f"cycle={cycle:>3}"
            f"  state={int(dut.state.value)}"
            f"  pc={hex(int(dut.pc.value))}"
            f"  instr={hex(int(dut.instruction_reg.value))}"
            f"  opcode={int(opcode):#04x}"
            f"  func3={int(func3):#04x}"
            f"  load_addr={hex(int(dut.load_addr.value))}"
        )

        await ClockCycles(dut.clk, 1)

    # final assertions
    # int(dut.waddr.value) == 0x40, (
    #    f"waddr: expected 0x40 got {hex(int(dut.waddr.value))}"
    # )
    assert read_memory(0x40, program) == 0x02, (
        f"memory[0x40]: expected 0x02 got {hex(read_memory(0x40, program))}"
    )
    assert int(dut.registers[r.a3].value) == 0x02, (
        f"a3: expected 0x02 got {hex(int(dut.registers[r.a3].value))}"
    )

    dut._log.info("All assertions passed ✓")
