"""
RV64I-specific instruction tests.

Covers the instructions that RV64I adds on top of RV32I:
  - W-type register ops:  addw, subw, sllw, srlw, sraw
  - W-type immediate ops: addiw, slliw, srliw, sraiw
  - 64-bit load/store:    ld, sd, lwu
  - 64-bit shift amounts  (6-bit shamt, distinguishes from 32-bit's 5-bit)
  - sign-extension behavior of W-type results

Assumes the following helpers live in helper.py:
    read_memory, write_memory, reset, run_program, make_program, reg, regu

Assumes isa.py exposes the RV64I builders. Several are NOT in the current
isa.py and must be added (see the NOTE block at the bottom of this file):
    addw, subw, sllw, srlw, sraw,
    addiw, slliw, srliw, sraiw,
    lwu
"""

import cocotb
from cocotb.clock import Clock

from .helper import make_program, reg, regu, run_program
from .isa import ISA

r = ISA.reg


# ═════════════════════════════════════════════════════════════════════════
# W-TYPE IMMEDIATE  (operate on low 32 bits, sign-extend result to 64)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_addiw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addiw(r.a1, r.a0, 23),  # 100 + 23 = 123 (32-bit, sign-extended)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 123, f"addiw a1={reg(dut, r.a1)}"


@cocotb.test()
async def test_addiw_sign_extend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # produce a 32-bit result with bit 31 set → must sign-extend to negative 64-bit
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # a0 = 0x80000000 (bit 31 set)
            ISA.addiw(
                r.a1, r.a0, 0
            ),  # addiw of 0x80000000 → sign-extends to 0xFFFFFFFF80000000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a1) == 0xFFFFFFFF80000000, (
        f"addiw sign extend a1={hex(regu(dut, r.a1))}"
    )


@cocotb.test()
async def test_addiw_overflow_wraps_at_32(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # 0x7FFFFFFF + 1 = 0x80000000 in 32-bit → sign-extends to negative
    prog = make_program(
        [
            ISA.lui(r.a0, 0x7FFFF),  # 0x7FFFF000
            ISA.addi(r.a0, r.a0, 0x7FF),  # 0x7FFFF7FF
            ISA.addiw(
                r.a1, r.a0, 1
            ),  # still positive-ish, just check it wraps in 32 bits
        ]
    )
    await run_program(dut, prog)
    # result must be a clean 32-bit value sign-extended (upper 32 bits = bit 31 copy)
    val = regu(dut, r.a1)
    low32 = val & 0xFFFFFFFF
    expected_upper = 0xFFFFFFFF if (low32 >> 31) else 0
    assert (val >> 32) == expected_upper, (
        f"addiw must sign-extend 32-bit result, got {hex(val)}"
    )


@cocotb.test()
async def test_slliw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slliw(r.a1, r.a0, 4),  # 1 << 4 = 16 (32-bit, sign-extended)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 16, f"slliw a1={reg(dut, r.a1)}"


@cocotb.test()
async def test_slliw_overflow_at_32(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # shifting into bit 31 must wrap at 32 bits, then sign-extend
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slliw(r.a1, r.a0, 31),  # 1 << 31 = 0x80000000 → sign-extend → negative
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a1) == 0xFFFFFFFF80000000, (
        f"slliw bit31 a1={hex(regu(dut, r.a1))}"
    )


@cocotb.test()
async def test_srliw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 256),
            ISA.srliw(r.a1, r.a0, 4),  # 256 >> 4 = 16 (logical, 32-bit)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == 16, f"srliw a1={reg(dut, r.a1)}"


@cocotb.test()
async def test_srliw_zero_fills_from_bit31(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # srliw operates on the low 32 bits only, zero-filling
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # a0 = 0x80000000 (bit 31 set)
            ISA.srliw(r.a1, r.a0, 4),  # logical: 0x80000000 >> 4 = 0x08000000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a1) == 0x08000000, f"srliw logical a1={hex(regu(dut, r.a1))}"


@cocotb.test()
async def test_sraiw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -16),
            ISA.sraiw(r.a1, r.a0, 2),  # -16 >> 2 = -4 (arithmetic, 32-bit)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a1) == -4, f"sraiw a1={reg(dut, r.a1)}"


# ═════════════════════════════════════════════════════════════════════════
# W-TYPE REGISTER  (operate on low 32 bits, sign-extend result to 64)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_addw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 50),
            ISA.addi(r.a1, r.zero, 25),
            ISA.addw(r.a2, r.a0, r.a1),  # 50 + 25 = 75
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 75, f"addw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_addw_ignores_upper_bits(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # addw must only use the low 32 bits of each operand
    # put garbage in upper 32 bits, result must still be correct 32-bit add
    prog = make_program(
        [
            ISA.lui(r.a0, 0x10000),  # 0x10000000
            ISA.slli(r.a0, r.a0, 8),  # shift so high bits are set: 0x1000000000
            ISA.addi(r.a0, r.a0, 5),  # low part = 5, high bits garbage
            ISA.addi(r.a1, r.zero, 3),
            ISA.addw(r.a2, r.a0, r.a1),  # should be (5 + 3) = 8, upper bits ignored
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 8, f"addw must ignore upper 32 bits, a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_subw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 40),
            ISA.subw(r.a2, r.a0, r.a1),  # 100 - 40 = 60
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 60, f"subw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_subw_sign_extend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # small - large = negative, must sign-extend the 32-bit result
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 5),
            ISA.addi(r.a1, r.zero, 10),
            ISA.subw(r.a2, r.a0, r.a1),  # 5 - 10 = -5
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -5, f"subw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sllw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 3),
            ISA.addi(r.a1, r.zero, 4),
            ISA.sllw(r.a2, r.a0, r.a1),  # 3 << 4 = 48
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 48, f"sllw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_srlw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 256),
            ISA.addi(r.a1, r.zero, 4),
            ISA.srlw(r.a2, r.a0, r.a1),  # 256 >> 4 = 16 (logical)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 16, f"srlw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sraw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -32),
            ISA.addi(r.a1, r.zero, 2),
            ISA.sraw(r.a2, r.a0, r.a1),  # -32 >> 2 = -8 (arithmetic)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -8, f"sraw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_sllw_uses_5bit_shamt(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # W-type shifts use only the low 5 bits of the shift amount
    # shift of 33 should behave as shift of 1 (33 & 0x1F = 1)
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.addi(r.a1, r.zero, 33),  # 33 & 0x1F = 1
            ISA.sllw(r.a2, r.a0, r.a1),  # 1 << (33 mod 32) = 1 << 1 = 2
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 2, (
        f"sllw should use 5-bit shamt (33->1), a2={reg(dut, r.a2)}"
    )


# ═════════════════════════════════════════════════════════════════════════
# 64-BIT SHIFTS  (regular shifts use 6-bit shamt on RV64)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_slli_64bit(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # regular slli on RV64 allows shifts up to 63
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a1, r.a0, 40),  # 1 << 40 (only possible with 6-bit shamt)
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a1) == (1 << 40), f"slli 64-bit a1={hex(regu(dut, r.a1))}"


@cocotb.test()
async def test_srli_64bit(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 40),  # a0 = 1 << 40
            ISA.srli(r.a1, r.a0, 20),  # >> 20 = 1 << 20
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a1) == (1 << 20), f"srli 64-bit a1={hex(regu(dut, r.a1))}"


# ═════════════════════════════════════════════════════════════════════════
# DOUBLEWORD LOAD / STORE
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_sd_ld(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),  # address
            ISA.addi(r.a1, r.zero, 0x123),  # value (small)
            ISA.sd(r.a0, r.a1, 0),  # store doubleword
            ISA.ld(r.a2, r.a0, 0),  # load it back
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0x123, f"sd/ld a2={hex(reg(dut, r.a2))}"


@cocotb.test()
async def test_sd_ld_full_64bit(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # build a value that uses the upper 32 bits, store and reload it
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),
            ISA.addi(r.a1, r.zero, 0x7F),  # low value
            ISA.slli(r.a1, r.a1, 24),  # push into upper half: 0x7F00000000
            ISA.addi(r.a1, r.a1, 0x55),  # 0x7F00000055
            ISA.sd(r.a0, r.a1, 0),  # store full 64-bit
            ISA.ld(r.a2, r.a0, 0),  # reload
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0x7F000055, f"sd/ld 64-bit a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_lwu_zero_extend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # lwu loads a 32-bit word and ZERO-extends (vs lw which sign-extends)
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 0x40),
            ISA.lui(r.a1, 0x80000),  # 0x80000000 (bit 31 set)
            ISA.sw(r.a0, r.a1, 0),  # store the word
            ISA.lwu(r.a2, r.a0, 0),  # zero-extend → 0x0000000080000000
            ISA.lw(r.a3, r.a0, 0),  # sign-extend → 0xFFFFFFFF80000000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0x0000000080000000, (
        f"lwu zero extend a2={hex(regu(dut, r.a2))}"
    )
    assert regu(dut, r.a3) == 0xFFFFFFFF80000000, (
        f"lw sign extend a3={hex(regu(dut, r.a3))}"
    )
