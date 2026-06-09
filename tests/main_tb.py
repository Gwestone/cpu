import copy
import struct
from os import getcwd, path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

bin_file_path = path.join(getcwd(), "bin/src/firmware.bin")
bin_file = open(bin_file_path, "rb")
binary_blob = bin_file.read()


def read_full(address, array):
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
async def immediate_add_operation(dut):
    """Try performing some computation."""
    cocotb.start_soon(Clock(dut.clk, 2).start())
    await reset(dut)

    blob_copy = copy.copy(binary_blob)
    program = [
        0x00000000,  # nop
        0x00200013,  # addi x0, x0, 2
        0x00200013,  # addi x0, x0, 2
        0x04008093,  # addi x1, x1, 64
        0x0000B023,  # sd x0, 0(x1)
        # end loop to prevent crash
        0x01400093,  # addi x1, x0, 24
        0x00008067,  # jalr x0, 0(x1) (infinite loop)
        0x00000000,  # nop
        0x00000000,  # nop
        0x00000000,  # nop
    ]

    blob = make_blob(program)

    print("Entire program blob: " + " ".join(hex(i) for i in blob))

    for _ in range(100 * 4):
        addr = int(dut.raddr.value)
        data = read_full(addr, blob)
        print("Reading address: " + hex(addr) + " (value: " + hex(data) + ")")
        dut.rdata.value = data
        await ClockCycles(dut.clk, 1)

    assert dut.waddr.value == 0x40
    assert dut.wdata.value == 0x04
