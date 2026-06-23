"""
RV64M (integer multiply / divide) instruction tests.

Covers the M extension on top of RV64I:
  - Multiply:        mul, mulh, mulhsu, mulhu
  - Divide/Rem:      div, divu, rem, remu
  - RV64 W-variants: mulw, divw, divuw, remw, remuw
  - Mandated edge cases: divide-by-zero, signed division overflow
  - Sign-extension behavior of the W-variants

Spec-mandated semantics exercised here (RISC-V Unpriv, M ext, v2.0):
  * Divide by zero:  quotient = all-ones, remainder = dividend
  * Signed overflow (most-negative / -1): quotient = dividend, remainder = 0
  * Unsigned overflow cannot occur
  * REMW/REMUW always sign-extend the 32-bit result, including on /0

Assumes the same helpers as the RV64I test file:
    make_program, reg, regu, run_program
and that isa.py exposes the M builders (see NOTE block at bottom):
    mul, mulh, mulhsu, mulhu, div, divu, rem, remu,
    mulw, divw, divuw, remw, remuw
"""

import cocotb
from cocotb.clock import Clock

from .helper import make_program, reg, regu, run_program
from .isa import ISA

r = ISA.reg

MASK64 = 0xFFFFFFFFFFFFFFFF
MIN64 = 0x8000000000000000  # most-negative 64-bit signed
MIN32 = 0x80000000  # most-negative 32-bit signed


# ═════════════════════════════════════════════════════════════════════════
# MULTIPLY  (full XLEN)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_mul(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 6),
            ISA.addi(r.a1, r.zero, 7),
            ISA.mul(r.a2, r.a0, r.a1),  # 6 * 7 = 42
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 42, f"mul a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_mul_negative(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -6),
            ISA.addi(r.a1, r.zero, 7),
            ISA.mul(r.a2, r.a0, r.a1),  # -6 * 7 = -42
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -42, f"mul negative a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_mul_returns_low_bits(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MUL returns the LOW XLEN bits of the product; build a product that
    # overflows 64 bits and check we keep only the low word.
    # a0 = 1 << 40, a1 = 1 << 40  ->  product = 1 << 80, low 64 bits = 0
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 40),
            ISA.addi(r.a1, r.zero, 1),
            ISA.slli(r.a1, r.a1, 40),
            ISA.mul(r.a2, r.a0, r.a1),  # low 64 bits of (1<<80) == 0
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0, f"mul low bits a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_mulh_signed(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MULH = upper 64 bits of signed*signed product.
    # a0 = 1 << 40, a1 = 1 << 40, product = 1 << 80,
    # upper 64 bits = (1 << 80) >> 64 = 1 << 16 = 0x10000
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 40),
            ISA.addi(r.a1, r.zero, 1),
            ISA.slli(r.a1, r.a1, 40),
            ISA.mulh(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0x10000, f"mulh a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_mulh_negative_result(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # signed * signed with one negative operand -> negative product,
    # upper bits must be all-ones (sign).
    # a0 = -(1<<40), a1 = (1<<40); product = -(1<<80)
    # upper 64 bits of a negative 128-bit value: 0xFFFFFFFFFFFF0000
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 40),
            ISA.sub(r.a0, r.zero, r.a0),  # a0 = -(1<<40)
            ISA.addi(r.a1, r.zero, 1),
            ISA.slli(r.a1, r.a1, 40),
            ISA.mulh(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    # -(1<<80) as 128-bit two's complement; high 64 bits:
    expected = (-(1 << 80) >> 64) & MASK64
    assert regu(dut, r.a2) == expected, f"mulh negative a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_mulhu_unsigned(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MULHU = upper 64 bits of unsigned*unsigned.
    # Use -1 (== 0xFFFF...FF unsigned) squared:
    # (2^64 - 1)^2 = 2^128 - 2^65 + 1 ; upper 64 bits = 2^64 - 2 = 0xFFFFFFFFFFFFFFFE
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -1),  # 0xFFFFFFFFFFFFFFFF
            ISA.addi(r.a1, r.zero, -1),
            ISA.mulhu(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0xFFFFFFFFFFFFFFFE, f"mulhu a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_mulhsu_mixed(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MULHSU = upper 64 bits of (signed rs1) * (unsigned rs2).
    # rs1 = -1 (signed), rs2 = 0xFFFFFFFFFFFFFFFF (unsigned, == 2^64 - 1)
    # product = -1 * (2^64 - 1) = -(2^64 - 1) = -(2^64)+1
    # as 128-bit two's complement, upper 64 bits = 0xFFFFFFFFFFFFFFFF
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -1),  # signed -1
            ISA.addi(r.a1, r.zero, -1),  # unsigned 2^64-1
            ISA.mulhsu(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    expected = (-(2**64 - 1) >> 64) & MASK64
    assert regu(dut, r.a2) == expected, f"mulhsu a2={hex(regu(dut, r.a2))}"


# ═════════════════════════════════════════════════════════════════════════
# DIVIDE / REMAINDER  (full XLEN)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_div(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.div(r.a2, r.a0, r.a1),  # 100 / 7 = 14 (toward zero)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 14, f"div a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_div_rounds_toward_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # signed division rounds toward zero: -7 / 2 = -3 (not -4)
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -7),
            ISA.addi(r.a1, r.zero, 2),
            ISA.div(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -3, f"div toward zero a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_divu(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # unsigned: -1 (== 2^64-1) / 2 = 0x7FFFFFFFFFFFFFFF
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -1),
            ISA.addi(r.a1, r.zero, 2),
            ISA.divu(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0x7FFFFFFFFFFFFFFF, f"divu a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_rem(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.rem(r.a2, r.a0, r.a1),  # 100 % 7 = 2
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 2, f"rem a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_rem_sign_follows_dividend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # For REM, the sign of a nonzero result equals the sign of the dividend.
    # -7 % 2 = -1
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -7),
            ISA.addi(r.a1, r.zero, 2),
            ISA.rem(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -1, f"rem sign a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_remu(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.remu(r.a2, r.a0, r.a1),  # 100 % 7 = 2
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 2, f"remu a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_div_consistency_identity(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # dividend = divisor*quotient + remainder  (except overflow)
    # 100 = 7*14 + 2  -> reconstruct and check == 100
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.div(r.a2, r.a0, r.a1),  # 14
            ISA.rem(r.a3, r.a0, r.a1),  # 2
            ISA.mul(r.a4, r.a2, r.a1),  # 14*7 = 98
            ISA.add(r.a5, r.a4, r.a3),  # 98 + 2 = 100
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a5) == 100, f"div identity a5={reg(dut, r.a5)}"


# ═════════════════════════════════════════════════════════════════════════
# DIVIDE-BY-ZERO  (spec-mandated results)
#   quotient  = all bits set (-1 signed / max unsigned)
#   remainder = dividend
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_div_by_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 123),
            ISA.addi(r.a1, r.zero, 0),
            ISA.div(r.a2, r.a0, r.a1),  # quotient = -1 (all ones)
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == MASK64, f"div/0 quotient a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_divu_by_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 123),
            ISA.addi(r.a1, r.zero, 0),
            ISA.divu(r.a2, r.a0, r.a1),  # quotient = all ones (max unsigned)
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == MASK64, f"divu/0 quotient a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_rem_by_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 123),
            ISA.addi(r.a1, r.zero, 0),
            ISA.rem(r.a2, r.a0, r.a1),  # remainder = dividend = 123
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 123, f"rem/0 a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_remu_by_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 123),
            ISA.addi(r.a1, r.zero, 0),
            ISA.remu(r.a2, r.a0, r.a1),  # remainder = dividend = 123
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 123, f"remu/0 a2={reg(dut, r.a2)}"


# ═════════════════════════════════════════════════════════════════════════
# SIGNED DIVISION OVERFLOW  (most-negative / -1)
#   quotient  = dividend (the most-negative value)
#   remainder = 0
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_div_overflow(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # build MIN64 = 1 << 63, then div by -1
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 63),  # a0 = 0x8000000000000000
            ISA.addi(r.a1, r.zero, -1),
            ISA.div(r.a2, r.a0, r.a1),  # overflow: quotient = dividend
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == MIN64, f"div overflow quotient a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_rem_overflow(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 63),  # a0 = MIN64
            ISA.addi(r.a1, r.zero, -1),
            ISA.rem(r.a2, r.a0, r.a1),  # overflow: remainder = 0
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"rem overflow a2={reg(dut, r.a2)}"


# ═════════════════════════════════════════════════════════════════════════
# W-VARIANTS  (operate on low 32 bits, sign-extend 32-bit result to 64)
# ═════════════════════════════════════════════════════════════════════════
@cocotb.test()
async def test_mulw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 6),
            ISA.addi(r.a1, r.zero, 7),
            ISA.mulw(r.a2, r.a0, r.a1),  # 42, sign-extended
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 42, f"mulw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_mulw_sign_extends(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # product whose low 32 bits have bit 31 set must sign-extend to negative.
    # 0x10000 * 0x10000 = 0x100000000; low 32 bits = 0, so use a case that
    # lands bit 31 set: 0x40000 * 0x2000 = 0x80000000 (bit 31 set)
    prog = make_program(
        [
            ISA.lui(r.a0, 0x40),  # a0 = 0x40000
            ISA.addi(r.a1, r.zero, 1),
            ISA.slli(r.a1, r.a1, 13),  # a1 = 0x2000
            ISA.mulw(r.a2, r.a0, r.a1),  # 0x40000 * 0x2000 = 0x80000000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0xFFFFFFFF80000000, (
        f"mulw sign extend a2={hex(regu(dut, r.a2))}"
    )


@cocotb.test()
async def test_mulw_ignores_upper_bits(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MULW multiplies only the low 32 bits of each source.
    # put garbage in upper bits of a0; result must be 5*3 = 15.
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 1),
            ISA.slli(r.a0, r.a0, 40),  # garbage high bit
            ISA.addi(r.a0, r.a0, 5),  # low 32 bits = 5
            ISA.addi(r.a1, r.zero, 3),
            ISA.mulw(r.a2, r.a0, r.a1),  # 5 * 3 = 15
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 15, f"mulw upper bits a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_divw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.divw(r.a2, r.a0, r.a1),  # 14, sign-extended
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 14, f"divw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_divw_negative_sign_extend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # negative 32-bit quotient must sign-extend to 64 bits
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.divw(r.a2, r.a0, r.a1),  # -100 / 7 = -14 (toward zero)
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -14, f"divw negative a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_divuw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # divuw treats the low 32 bits as unsigned.
    # 0x80000000 / 2 = 0x40000000 (positive, bit 31 clear -> sign-ext is no-op)
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # 0x80000000
            ISA.addi(r.a1, r.zero, 2),
            ISA.divuw(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0x40000000, f"divuw a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_remw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.remw(r.a2, r.a0, r.a1),  # 100 % 7 = 2
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 2, f"remw a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_remw_sign_follows_dividend(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # -7 % 2 = -1, sign-extended to 64 bits
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, -7),
            ISA.addi(r.a1, r.zero, 2),
            ISA.remw(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == -1, f"remw sign a2={reg(dut, r.a2)}"


@cocotb.test()
async def test_remuw(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 100),
            ISA.addi(r.a1, r.zero, 7),
            ISA.remuw(r.a2, r.a0, r.a1),  # 2
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 2, f"remuw a2={reg(dut, r.a2)}"


# ── W-variant divide-by-zero (32-bit width, still sign-extended) ──────────
@cocotb.test()
async def test_divw_by_zero(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # quotient all-ones over 32 bits -> 0xFFFFFFFF, sign-extended -> -1
    prog = make_program(
        [
            ISA.addi(r.a0, r.zero, 123),
            ISA.addi(r.a1, r.zero, 0),
            ISA.divw(r.a2, r.a0, r.a1),
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == MASK64, f"divw/0 a2={hex(regu(dut, r.a2))}"


@cocotb.test()
async def test_remw_by_zero_sign_extends(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # REMW remainder = dividend (low 32 bits), sign-extended to 64.
    # Use a dividend whose low-32 bit 31 is set so sign-extension is observable.
    # 0x80000123 as 32-bit -> sign-extends to 0xFFFFFFFF80000123
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # 0x80000000
            ISA.addi(r.a0, r.a0, 0x123),  # 0x80000123
            ISA.addi(r.a1, r.zero, 0),
            ISA.remw(r.a2, r.a0, r.a1),  # remainder = dividend, sign-extended
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0xFFFFFFFF80000123, (
        f"remw/0 sign extend a2={hex(regu(dut, r.a2))}"
    )


# ── W-variant signed overflow (MIN32 / -1) ────────────────────────────────
@cocotb.test()
async def test_divw_overflow(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MIN32 / -1 overflow: quotient = dividend = MIN32, sign-extended
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # 0x80000000 = MIN32
            ISA.addi(r.a1, r.zero, -1),
            ISA.divw(r.a2, r.a0, r.a1),  # quotient = MIN32 -> 0xFFFFFFFF80000000
        ]
    )
    await run_program(dut, prog)
    assert regu(dut, r.a2) == 0xFFFFFFFF80000000, (
        f"divw overflow a2={hex(regu(dut, r.a2))}"
    )


@cocotb.test()
async def test_remw_overflow(dut):
    cocotb.start_soon(Clock(dut.clk, 2).start())
    # MIN32 / -1 overflow: remainder = 0
    prog = make_program(
        [
            ISA.lui(r.a0, 0x80000),  # MIN32
            ISA.addi(r.a1, r.zero, -1),
            ISA.remw(r.a2, r.a0, r.a1),  # remainder = 0
        ]
    )
    await run_program(dut, prog)
    assert reg(dut, r.a2) == 0, f"remw overflow a2={reg(dut, r.a2)}"


# ═════════════════════════════════════════════════════════════════════════
# NOTE: builders required in isa.py for these tests
#
#   All are R-type, funct7 = 0b0000001.
#   OP    (opcode 0b0110011): mul, mulh, mulhsu, mulhu, div, divu, rem, remu
#       funct3: mul=000 mulh=001 mulhsu=010 mulhu=011
#               div=100 divu=101 rem=110 remu=111
#   OP-32 (opcode 0b0111011): mulw, divw, divuw, remw, remuw
#       funct3: mulw=000 divw=100 divuw=101 remw=110 remuw=111
#               (no mulhw / no divuw-high; 010/011 unused in OP-32 for M)
# ═════════════════════════════════════════════════════════════════════════
