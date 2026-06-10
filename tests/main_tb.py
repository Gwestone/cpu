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


def read_full(address, array):
    if address == 0x40:
        return 0x02
    return (
        (array[address] << 0)  # first byte = least significant
        | (array[address + 1] << 8)
        | (array[address + 2] << 16)
        | (array[address + 3] << 24)  # last byte = most significant
    )


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
    program = [
        ISA.nop(),  # nop
        ISA.addi(r.a1, r.zero, 2),  # addi x2, x2, 2
        ISA.addi(r.a2, r.zero, 64),  # addi x1, x1, 64
        ISA.sd(r.a2, r.a1, 0),  # sd x2, 0(x1)
        # clear a1 and load our saved value back into x1
        ISA.addi(r.a1, r.zero, 0),  # addi x2, x0, 0
        ISA.lb(r.a1, r.a2, 0),  # ld x1, 0(x2)
        # end loop to prevent crash
        ISA.addi(r.a1, r.zero, 24),  # addi x1, x0, 24
        ISA.jalr(r.zero, r.a1, 0),  # jalr x0, 0(x1) (infinite loop)
    ]

    blob = ISA.make_blob(program)

    print("Entire program blob: " + " ".join(hex(i) for i in blob))

    for _ in range(len(program) + 1):
        addr = int(dut.raddr.value)
        data = read_full(addr, blob)
        print("Reading address: " + hex(addr) + " (value: " + hex(data) + ")")
        dut.rdata.value = data
        await ClockCycles(dut.clk, 1)

    assert dut.waddr.value == 0x40
    assert dut.wdata.value == 0x02
    assert dut.registers[r.a1].value == 0x02
