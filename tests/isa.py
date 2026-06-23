# isa.py
import struct


class Reg:
    def __init__(self):
        for i in range(32):
            setattr(self, f"x{i}", i)
        # ABI names
        self.zero = 0
        self.ra = 1
        self.sp = 2
        self.gp = 3
        self.tp = 4
        self.t0 = 5
        self.t1 = 6
        self.t2 = 7
        self.s0 = 8
        self.s1 = 9
        self.a0 = 10
        self.a1 = 11
        self.a2 = 12
        self.a3 = 13
        self.a4 = 14
        self.a5 = 15
        self.a6 = 16
        self.a7 = 17
        self.s2 = 18
        self.s3 = 19
        self.s4 = 20
        self.s5 = 21
        self.s6 = 22
        self.s7 = 23
        self.s8 = 24
        self.s9 = 25
        self.s10 = 26
        self.s11 = 27
        self.t3 = 28
        self.t4 = 29
        self.t5 = 30
        self.t6 = 31


class ISA:
    reg = Reg()

    # ── I-type ──────────────────────────────────────────────
    @staticmethod
    def _i(opcode, funct3, rd, rs1, imm, funct7=0):
        imm = imm & 0xFFF
        return (
            (funct7 << 25)
            | (imm << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | opcode
        )

    @staticmethod
    def addi(rd, rs1, imm):
        return ISA._i(0x13, 0x0, rd, rs1, imm)

    @staticmethod
    def slli(rd, rs1, imm):
        return ISA._i(0x13, 0x1, rd, rs1, imm, funct7=0x00)

    @staticmethod
    def slti(rd, rs1, imm):
        return ISA._i(0x13, 0x2, rd, rs1, imm)

    @staticmethod
    def sltiu(rd, rs1, imm):
        return ISA._i(0x13, 0x3, rd, rs1, imm)

    @staticmethod
    def xori(rd, rs1, imm):
        return ISA._i(0x13, 0x4, rd, rs1, imm)

    @staticmethod
    def srli(rd, rs1, imm):
        return ISA._i(0x13, 0x5, rd, rs1, imm, funct7=0x00)

    @staticmethod
    def srai(rd, rs1, imm):
        return ISA._i(0x13, 0x5, rd, rs1, imm, funct7=0x20)

    @staticmethod
    def ori(rd, rs1, imm):
        return ISA._i(0x13, 0x6, rd, rs1, imm)

    @staticmethod
    def andi(rd, rs1, imm):
        return ISA._i(0x13, 0x7, rd, rs1, imm)

    @staticmethod
    def jalr(rd, rs1, imm):
        return ISA._i(0x67, 0x0, rd, rs1, imm)

    @staticmethod
    def lb(rd, rs1, imm):
        return ISA._i(0x03, 0x0, rd, rs1, imm)

    @staticmethod
    def lbu(rd, rs1, imm):
        return ISA._i(0x03, 0x4, rd, rs1, imm)

    @staticmethod
    def lh(rd, rs1, imm):
        return ISA._i(0x03, 0x1, rd, rs1, imm)

    @staticmethod
    def lw(rd, rs1, imm):
        return ISA._i(0x03, 0x2, rd, rs1, imm)

    @staticmethod
    def ld(rd, rs1, imm):
        return ISA._i(0x03, 0x3, rd, rs1, imm)

    # ── R-type ──────────────────────────────────────────────
    @staticmethod
    def _r(funct7, funct3, rd, rs1, rs2):
        return (
            (funct7 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | 0x33
        )

    @staticmethod
    def add(rd, rs1, rs2):
        return ISA._r(0x00, 0x0, rd, rs1, rs2)

    @staticmethod
    def sub(rd, rs1, rs2):
        return ISA._r(0x20, 0x0, rd, rs1, rs2)

    @staticmethod
    def sll(rd, rs1, rs2):
        return ISA._r(0x00, 0x1, rd, rs1, rs2)

    @staticmethod
    def slt(rd, rs1, rs2):
        return ISA._r(0x00, 0x2, rd, rs1, rs2)

    @staticmethod
    def sltu(rd, rs1, rs2):
        return ISA._r(0x00, 0x3, rd, rs1, rs2)

    @staticmethod
    def xor(rd, rs1, rs2):
        return ISA._r(0x00, 0x4, rd, rs1, rs2)

    @staticmethod
    def srl(rd, rs1, rs2):
        return ISA._r(0x00, 0x5, rd, rs1, rs2)

    @staticmethod
    def sra(rd, rs1, rs2):
        return ISA._r(0x20, 0x5, rd, rs1, rs2)

    @staticmethod
    def or_(rd, rs1, rs2):
        return ISA._r(0x00, 0x6, rd, rs1, rs2)

    @staticmethod
    def and_(rd, rs1, rs2):
        return ISA._r(0x00, 0x7, rd, rs1, rs2)

    # ── S-type ──────────────────────────────────────────────
    @staticmethod
    def _s(funct3, rs1, rs2, imm):
        imm = imm & 0xFFF
        return (
            ((imm >> 5) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | ((imm & 0x1F) << 7)
            | 0x23
        )

    @staticmethod
    def sb(rs1, rs2, imm):
        return ISA._s(0x0, rs1, rs2, imm)

    @staticmethod
    def sh(rs1, rs2, imm):
        return ISA._s(0x1, rs1, rs2, imm)

    @staticmethod
    def sw(rs1, rs2, imm):
        return ISA._s(0x2, rs1, rs2, imm)

    @staticmethod
    def sd(rs1, rs2, imm):
        return ISA._s(0x3, rs1, rs2, imm)

    # ── B-type ──────────────────────────────────────────────
    @staticmethod
    def _b(funct3, rs1, rs2, imm):
        imm = imm & 0x1FFF
        b12 = (imm >> 12) & 1
        b11 = (imm >> 11) & 1
        b10_5 = (imm >> 5) & 0x3F
        b4_1 = (imm >> 1) & 0xF
        return (
            (b12 << 31)
            | (b10_5 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (b4_1 << 8)
            | (b11 << 7)
            | 0x63
        )

    @staticmethod
    def beq(rs1, rs2, imm):
        return ISA._b(0x0, rs1, rs2, imm)

    @staticmethod
    def bne(rs1, rs2, imm):
        return ISA._b(0x1, rs1, rs2, imm)

    @staticmethod
    def blt(rs1, rs2, imm):
        return ISA._b(0x4, rs1, rs2, imm)

    @staticmethod
    def bge(rs1, rs2, imm):
        return ISA._b(0x5, rs1, rs2, imm)

    @staticmethod
    def bltu(rs1, rs2, imm):
        return ISA._b(0x6, rs1, rs2, imm)

    @staticmethod
    def bgeu(rs1, rs2, imm):
        return ISA._b(0x7, rs1, rs2, imm)

    # ── U-type ──────────────────────────────────────────────
    @staticmethod
    def lui(rd, imm):
        return ((imm & 0xFFFFF) << 12) | (rd << 7) | 0x37

    @staticmethod
    def auipc(rd, imm):
        return ((imm & 0xFFFFF) << 12) | (rd << 7) | 0x17

    # ── J-type ──────────────────────────────────────────────
    @staticmethod
    def jal(rd, imm):
        imm = imm & 0x1FFFFF
        b20 = (imm >> 20) & 1
        b10_1 = (imm >> 1) & 0x3FF
        b11 = (imm >> 11) & 1
        b19_12 = (imm >> 12) & 0xFF
        return (
            (b20 << 31)
            | (b10_1 << 21)
            | (b11 << 20)
            | (b19_12 << 12)
            | (rd << 7)
            | 0x6F
        )

    # ── pseudoinstructions ──────────────────────────────────
    @staticmethod
    def nop():
        return ISA.addi(0, 0, 0)

    @staticmethod
    def li(rd, imm):
        return ISA.addi(rd, 0, imm)

    @staticmethod
    def mv(rd, rs):
        return ISA.addi(rd, rs, 0)

    @staticmethod
    def j(imm):
        return ISA.jal(0, imm)

    @staticmethod
    def ret():
        return ISA.jalr(0, 1, 0)

    # ── utility ─────────────────────────────────────────────
    @staticmethod
    def make_blob(words):
        b = bytearray()
        for w in words:
            b += struct.pack("<I", w)
        return b

    #   # W-type I (opcode 0x1B)

    @staticmethod
    def addiw(rd, rs1, imm):
        return ISA._i(0x1B, 0x0, rd, rs1, imm)

    @staticmethod
    def slliw(rd, rs1, imm):
        return ISA._i(0x1B, 0x1, rd, rs1, imm, funct7=0x00)

    @staticmethod
    def srliw(rd, rs1, imm):
        return ISA._i(0x1B, 0x5, rd, rs1, imm, funct7=0x00)

    @staticmethod
    def sraiw(rd, rs1, imm):
        return ISA._i(0x1B, 0x5, rd, rs1, imm, funct7=0x20)

    # W-type R (opcode 0x3B)
    @staticmethod
    def addw(rd, rs1, rs2):
        return ISA._rw(0x00, 0x0, rd, rs1, rs2)

    @staticmethod
    def subw(rd, rs1, rs2):
        return ISA._rw(0x20, 0x0, rd, rs1, rs2)

    @staticmethod
    def sllw(rd, rs1, rs2):
        return ISA._rw(0x00, 0x1, rd, rs1, rs2)

    @staticmethod
    def srlw(rd, rs1, rs2):
        return ISA._rw(0x00, 0x5, rd, rs1, rs2)

    @staticmethod
    def sraw(rd, rs1, rs2):
        return ISA._rw(0x20, 0x5, rd, rs1, rs2)

    # ═════════════════════════════════════════════════════════════════════════
    # RV32M / Base M-Extension (Opcode: 0x33, funct7: 0x01)
    # ═════════════════════════════════════════════════════════════════════════
    @staticmethod
    def mul(rd, rs1, rs2):
        return ISA._m(0x33, 0x0, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def mulh(rd, rs1, rs2):
        return ISA._m(0x33, 0x1, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def mulhsu(rd, rs1, rs2):
        return ISA._m(0x33, 0x2, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def mulhu(rd, rs1, rs2):
        return ISA._m(0x33, 0x3, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def div(rd, rs1, rs2):
        return ISA._m(0x33, 0x4, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def divu(rd, rs1, rs2):
        return ISA._m(0x33, 0x5, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def rem(rd, rs1, rs2):
        return ISA._m(0x33, 0x6, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def remu(rd, rs1, rs2):
        return ISA._m(0x33, 0x7, rd, rs1, rs2, funct7=0x01)

    # ═════════════════════════════════════════════════════════════════════════
    # RV64M / W-Type M-Extension (Opcode: 0x3B, funct7: 0x01)
    # ═════════════════════════════════════════════════════════════════════════
    @staticmethod
    def mulw(rd, rs1, rs2):
        return ISA._m(0x3B, 0x0, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def divw(rd, rs1, rs2):
        return ISA._m(0x3B, 0x4, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def divuw(rd, rs1, rs2):
        return ISA._m(0x3B, 0x5, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def remw(rd, rs1, rs2):
        return ISA._m(0x3B, 0x6, rd, rs1, rs2, funct7=0x01)

    @staticmethod
    def remuw(rd, rs1, rs2):
        return ISA._m(0x3B, 0x7, rd, rs1, rs2, funct7=0x01)

    # helper for W-type R (opcode 0x3B instead of 0x33)
    @staticmethod
    def _rw(funct7, funct3, rd, rs1, rs2):
        return (
            (funct7 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | 0x3B
        )

    # lwu (opcode 0x03, funct3 0x6)
    @staticmethod
    def lwu(rd, rs1, imm):
        return ISA._i(0x03, 0x6, rd, rs1, imm)

    @staticmethod
    def _m(opcode, funct3, rd, rs1, rs2, funct7=0):
        return (
            (funct7 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | opcode
        )
