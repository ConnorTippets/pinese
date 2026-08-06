from .util import sign_convert_byte, page_of
from .memory import CPUMemory, PPUMemory

# As much as I love my code formatter, it hates needless spaces
# I like needless spaces. Looks neat.
# fmt: off
CARRY_FLAG             = 0b00000001
ZERO_FLAG              = 0b00000010
INTERRUPT_DISABLE_FLAG = 0b00000100
DECIMAL_FLAG           = 0b00001000
B_FLAG                 = 0b00010000
OVERFLOW_FLAG          = 0b01000000
NEGATIVE_FLAG          = 0b10000000
# fmt: on


class CPU:
    def __init__(self):
        self.memory: CPUMemory
        self.ppumemory: PPUMemory

        self.a = 0
        self.x = 0
        self.y = 0
        self.p = 0x24
        self.sp = 0x100  # SP is set in reset

        self.stacknum = 0

        self.cycles = 0

    def reset(self):
        self.pc = self.memory.read_word(0xFFFC)

        self.sp -= 3
        if self.sp < 0:
            self.sp += 0x100

        self.p |= INTERRUPT_DISABLE_FLAG

    def read_pc_byte(self) -> int:
        out = self.memory.read_byte(self.pc)
        self.pc += 1
        return out

    def read_pc_word(self) -> int:
        out = self.memory.read_word(self.pc)
        self.pc += 2
        return out

    def set_flag(self, flag: int, value):
        if value:
            self.p |= flag
        else:
            self.p &= ~flag

    def push_byte(self, value: int):
        self.memory.write_byte(0x100 + self.sp, value)
        self.sp -= 1

    def push_word(self, value: int):
        self.push_byte((value >> 8) & 0xFF)
        self.push_byte(value & 0xFF)

    def pop_byte(self) -> int:
        self.sp += 1
        return self.memory.read_byte(0x100 + self.sp)

    def pop_word(self) -> int:
        return self.pop_byte() | (self.pop_byte() << 8)

    def _ora(self, val: int):
        self.a |= val

        self.set_flag(ZERO_FLAG, self.a == 0)
        self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

    def _and(self, val: int):
        self.a &= val

        self.set_flag(ZERO_FLAG, self.a == 0)
        self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

    def _ldx(self, val: int):
        self.x = val

        self.set_flag(ZERO_FLAG, self.x == 0)
        self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

    def _lda(self, val: int):
        self.a = val

        self.set_flag(ZERO_FLAG, self.a == 0)
        self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

    def _branch(self, condition):
        rel = sign_convert_byte(self.read_pc_byte())

        self.cycles += 2

        if condition:
            self.pc += rel  # + 2 was handled already

            self.cycles += 1

            if not page_of(self.pc - rel) == page_of(self.pc):
                self.cycles += 1

    def _bit(self, val: int):
        self.set_flag(ZERO_FLAG, (self.a & val) == 0)
        self.set_flag(OVERFLOW_FLAG, val & OVERFLOW_FLAG)
        self.set_flag(NEGATIVE_FLAG, val & NEGATIVE_FLAG)

    def _lsr(self, val: int) -> int:
        result = val >> 1

        self.set_flag(CARRY_FLAG, val & CARRY_FLAG)
        self.set_flag(ZERO_FLAG, result == 0)
        self.set_flag(NEGATIVE_FLAG, 0)

        return result

    def _asl(self, val: int) -> int:
        result = (val << 1) & 0xFF

        self.set_flag(CARRY_FLAG, val & NEGATIVE_FLAG)
        self.set_flag(ZERO_FLAG, result == 0)
        self.set_flag(NEGATIVE_FLAG, result & NEGATIVE_FLAG)

        return result

    def _ror(self, val: int) -> int:
        result = val >> 1 | ((self.p & CARRY_FLAG) << 7)

        self.set_flag(CARRY_FLAG, val & CARRY_FLAG)
        self.set_flag(ZERO_FLAG, result == 0)
        self.set_flag(NEGATIVE_FLAG, result & NEGATIVE_FLAG)

        return result

    def _rol(self, val: int) -> int:
        result = (val << 1 | (self.p & CARRY_FLAG)) & 0xFF

        self.set_flag(CARRY_FLAG, val & NEGATIVE_FLAG)
        self.set_flag(ZERO_FLAG, result == 0)
        self.set_flag(NEGATIVE_FLAG, result & NEGATIVE_FLAG)

        return result

    def step(self) -> int:
        opcode = self.read_pc_byte()
        self.cycles = 0

        new_interrupts_state = ""
        match opcode:
            case 0x01:
                # ORA (indirect,x)
                addr = self.read_pc_byte()
                self._ora(
                    self.memory.read_byte(
                        self.memory.read_byte((addr + self.x) & 0xFF)
                        + self.memory.read_byte((addr + self.x + 1) & 0xFF) * 256
                    )
                )

                self.cycles += 6
            case 0x05:
                # ORA zpg
                self._ora(self.memory.read_byte(self.read_pc_byte()))

                self.cycles += 3
            case 0x06:
                # ASL zpg
                addr = self.read_pc_byte()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._asl(val))

                self.cycles += 5
            case 0x08:
                # PHP
                self.push_byte(self.p | B_FLAG)

                self.cycles += 3
            case 0x09:
                # ORA imm
                self._ora(self.read_pc_byte())

                self.cycles += 2
            case 0x0A:
                # ASL a
                self.a = self._asl(self.a)

                self.cycles += 2
            case 0x0D:
                # ORA abs
                self._ora(self.memory.read_byte(self.read_pc_word()))

                self.cycles += 4
            case 0x0E:
                # ASL abs
                addr = self.read_pc_word()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._asl(val))

                self.cycles += 6
            case 0x10:
                # BPL rel
                self._branch(not self.p & NEGATIVE_FLAG)
            case 0x11:
                # ORA (indirect),y
                addr = self.read_pc_byte()
                base = (
                    self.memory.read_byte(addr)
                    + self.memory.read_byte((addr + 1) & 0xFF) * 256
                )
                self._ora(self.memory.read_byte(base + self.y))

                self.cycles += 5

                if not page_of(base) == page_of(base + self.y):
                    self.cycles += 1
            case 0x15:
                # ORA zpg,x
                self._ora(self.memory.read_byte((self.read_pc_byte() + self.x) & 0xFF))

                self.cycles += 4
            case 0x16:
                # ASL zpg,x
                addr = (self.read_pc_byte() + self.x) & 0xFF
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._asl(val))

                self.cycles += 6
            case 0x18:
                # CLC
                self.set_flag(CARRY_FLAG, 0)

                self.cycles += 2
            case 0x19:
                # ORA abs,y
                addr = self.read_pc_word()
                self._ora(self.memory.read_byte(addr + self.y))

                self.cycles += 4

                if not page_of(addr) == page_of(self.y):
                    self.cycles += 1
            case 0x1D:
                # ORA abs,x
                addr = self.read_pc_word()
                self._ora(self.memory.read_byte(addr + self.x))

                self.cycles += 4

                if not page_of(addr) == page_of(self.x):
                    self.cycles += 1
            case 0x1E:
                # ASL abs,x
                addr = self.read_pc_word() + self.x
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._asl(val))

                self.cycles += 7
            case 0x20:
                # JSR abs
                location = self.read_pc_word()
                self.push_word(self.pc - 1)

                self.pc = location
                self.cycles += 6
            case 0x21:
                # AND (indirect,x)
                addr = self.read_pc_byte()
                self._and(
                    self.memory.read_byte(
                        self.memory.read_byte((addr + self.x) & 0xFF)
                        + self.memory.read_byte((addr + self.x + 1) & 0xFF) * 256
                    )
                )

                self.cycles += 6
            case 0x24:
                # BIT zpg
                self._bit(self.memory.read_byte(self.read_pc_byte()))
                self.cycles += 3
            case 0x25:
                # AND zpg
                self._and(self.memory.read_byte(self.read_pc_byte()))
                self.cycles += 3
            case 0x26:
                # ROL zpg
                addr = self.read_pc_byte()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._rol(val))

                self.cycles += 5
            case 0x28:
                # PLP
                val = self.pop_byte()

                self.set_flag(CARRY_FLAG, val & CARRY_FLAG)
                self.set_flag(ZERO_FLAG, val & ZERO_FLAG)
                self.new_interrupts_state = (
                    "disabled" if val & INTERRUPT_DISABLE_FLAG else "enabled"
                )
                self.set_flag(DECIMAL_FLAG, val & DECIMAL_FLAG)
                self.set_flag(OVERFLOW_FLAG, val & OVERFLOW_FLAG)
                self.set_flag(NEGATIVE_FLAG, val & NEGATIVE_FLAG)

                self.cycles += 4
            case 0x29:
                # AND imm
                self._and(self.read_pc_byte())
                self.cycles += 2
            case 0x2A:
                # ROL a
                self.a = self._rol(self.a)

                self.cycles += 2
            case 0x2C:
                # BIT abs
                self._bit(self.memory.read_byte(self.read_pc_word()))
                self.cycles += 4
            case 0x2D:
                # AND abs
                self._and(self.memory.read_byte(self.read_pc_word()))
                self.cycles += 4
            case 0x2E:
                # ROL abs
                addr = self.read_pc_word()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._rol(val))

                self.cycles += 6
            case 0x30:
                # BMI rel
                self._branch(self.p & NEGATIVE_FLAG)
            case 0x35:
                # AND zpg,x
                self._and(self.memory.read_byte((self.read_pc_byte() + self.x) & 0xFF))
                self.cycles += 4
            case 0x31:
                # AND (indirect),y
                addr = self.read_pc_byte()
                base = (
                    self.memory.read_byte(addr)
                    + self.memory.read_byte((addr + 1) & 0xFF) * 256
                )
                self._and(self.memory.read_byte(base + self.y))

                self.cycles += 5

                if not page_of(base) == page_of(base + self.y):
                    self.cycles += 1
            case 0x36:
                # ROL zpg,x
                addr = (self.read_pc_byte() + self.x) & 0xFF
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._rol(val))

                self.cycles += 6
            case 0x38:
                # SEC
                self.set_flag(CARRY_FLAG, 1)

                self.cycles += 2
            case 0x39:
                # AND abs,y
                addr = self.read_pc_word()
                self._and(self.memory.read_byte(addr + self.y))
                self.cycles += 4

                if not page_of(addr) == page_of(addr + self.y):
                    self.cycles += 1
            case 0x3D:
                # AND abs,x
                addr = self.read_pc_word()
                self._and(self.memory.read_byte(addr + self.x))
                self.cycles += 4

                if not page_of(addr) == page_of(addr + self.x):
                    self.cycles += 1
            case 0x3E:
                # ROL abs,x
                addr = self.read_pc_word() + self.x
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._rol(val))

                self.cycles += 7
            case 0x40:
                # RTI
                p = self.pop_byte()

                self.set_flag(CARRY_FLAG, p & CARRY_FLAG)
                self.set_flag(ZERO_FLAG, p & ZERO_FLAG)
                self.set_flag(INTERRUPT_DISABLE_FLAG, p & INTERRUPT_DISABLE_FLAG)
                self.set_flag(DECIMAL_FLAG, p & DECIMAL_FLAG)
                self.set_flag(OVERFLOW_FLAG, p & OVERFLOW_FLAG)
                self.set_flag(NEGATIVE_FLAG, p & NEGATIVE_FLAG)

                self.pc = self.pop_word()

                self.cycles += 6
            case 0x46:
                # LSR zpg
                addr = self.read_pc_byte()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._lsr(val))

                self.cycles += 5
            case 0x48:
                # PHA
                self.push_byte(self.a)

                self.cycles += 3
            case 0x49:
                # EOR
                imm = self.read_pc_byte()
                self.a ^= imm

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0x4A:
                # LSR a
                self.a = self._lsr(self.a)

                self.cycles += 2
            case 0x4C:
                # JMP abs
                location = self.read_pc_word()

                self.pc = location
                self.cycles += 3
            case 0x4E:
                # LSR abs
                addr = self.read_pc_word()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._lsr(val))

                self.cycles += 6
            case 0x50:
                # BVC rel
                self._branch(not self.p & OVERFLOW_FLAG)
            case 0x56:
                # LSR zpg,x
                addr = (self.read_pc_byte() + self.x) & 0xFF
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._lsr(val))

                self.cycles += 6
            case 0x5E:
                # LSR abs,x
                addr = self.read_pc_word() + self.x
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._lsr(val))

                self.cycles += 7
            case 0x60:
                # RTS
                self.pc = self.pop_word() + 1
            case 0x68:
                # PLA
                self.a = self.pop_byte()

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 4
            case 0x69:
                # ADC imm
                imm = self.read_pc_byte()

                prev_a = self.a
                new_a = self.a + imm + (self.p & CARRY_FLAG)
                self.a = new_a & 0xFF

                self.set_flag(CARRY_FLAG, new_a > 0xFF)
                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(OVERFLOW_FLAG, (self.a ^ prev_a) & (self.a ^ imm) & 0x80)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0x6A:
                # ROR a
                self.a = self._ror(self.a)

                self.cycles += 2
            case 0x66:
                # ROR zpg
                addr = self.read_pc_byte()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._ror(val))

                self.cycles += 5
            case 0x6E:
                # ROR abs
                addr = self.read_pc_word()
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._ror(val))

                self.cycles += 6
            case 0x70:
                # BVS rel
                self._branch(self.p & OVERFLOW_FLAG)
            case 0x76:
                # ROR zpg,x
                addr = (self.read_pc_byte() + self.x) & 0xFF
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._ror(val))

                self.cycles += 6
            case 0x78:
                # SEI
                new_interrupts_state = "disabled"
            case 0x7E:
                # ROR abs,x
                addr = self.read_pc_word() + self.x
                val = self.memory.read_byte(addr)

                self.memory.write_byte(addr, val)
                self.memory.write_byte(addr, self._ror(val))

                self.cycles += 7
            case 0x81:
                # STA (indirect,x)
                base = self.read_pc_word()
                addr = self.memory.read_byte(
                    self.memory.read_byte((base + self.x) & 0xFF)
                    + self.memory.read_byte((base + self.x + 1) & 0xFF) * 256
                )

                self.memory.write_byte(addr, self.a)
                self.cycles += 6
            case 0x85:
                # STA zpg
                addr = self.read_pc_byte()

                self.memory.write_byte(addr, self.a)
                self.cycles += 3
            case 0x86:
                # STX zpg
                addr = self.read_pc_byte()

                self.memory.write_byte(addr, self.x)
                self.cycles += 3
            case 0x88:
                # DEY
                self.y = (self.y - 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                self.cycles += 2
            case 0x8A:
                # TXA
                self.a = self.x

                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                self.cycles += 2
            case 0x8D:
                # STA abs
                addr = self.read_pc_word()

                self.memory.write_byte(addr, self.a)
                self.cycles += 4
            case 0x8E:
                # STX abs
                addr = self.read_pc_word()

                self.memory.write_byte(addr, self.x)
                self.cycles += 4
            case 0x90:
                # BCC rel
                self._branch(not self.p & CARRY_FLAG)
            case 0x91:
                # STA (indirect),y
                base = self.read_pc_word()
                addr = self.memory.read_byte(
                    self.memory.read_byte(base)
                    + self.memory.read_byte((base + 1) & 0xFF) * 256
                    + self.y
                )

                self.memory.write_byte(addr, self.a)
                self.cycles += 6
            case 0x95:
                # STA zpg,x
                addr = (self.read_pc_byte() + self.x) & 0xFF

                self.memory.write_byte(addr, self.a)
                self.cycles += 3
            case 0x96:
                # STX zpg,y
                addr = (self.read_pc_byte() + self.y) & 0xFF

                self.memory.write_byte(addr, self.x)
                self.cycles += 4
            case 0x98:
                # TYA
                self.a = self.y

                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                self.cycles += 2
            case 0x99:
                # STA abs,y
                addr = self.read_pc_word() + self.y

                self.memory.write_byte(addr, self.a)
                self.cycles += 5
            case 0x9A:
                # TXS
                self.sp = self.x

                self.cycles += 2
            case 0x9D:
                # STA abs,x
                addr = self.read_pc_word() + self.x

                self.memory.write_byte(addr, self.a)
                self.cycles += 5
            case 0xA0:
                # LDY imm
                imm = self.read_pc_byte()

                self.y = imm
                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xA2:
                # LDX imm
                imm = self.read_pc_byte()
                self._ldx(imm)
                self.cycles += 2
            case 0xA6:
                # LDX zpg
                addr = self.read_pc_byte()
                self._ldx(self.memory.read_byte(addr))
                self.cycles += 3
            case 0xA5:
                # LDA zpg
                addr = self.read_pc_byte()
                self._lda(self.memory.read_byte(addr))
                self.cycles += 3
            case 0xA8:
                # TAY
                self.y = self.a

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xA9:
                # LDA imm
                imm = self.read_pc_byte()
                self._lda(imm)
                self.cycles += 2
            case 0xA9:
                # LDA imm
                imm = self.read_pc_byte()

                self.a = imm
                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xAA:
                # TAX
                self.x = self.a

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xAD:
                # LDA abs
                addr = self.read_pc_word()
                self._lda(self.memory.read_byte(addr))
                self.cycles += 4
            case 0xAE:
                # LDX abs
                addr = self.read_pc_word()
                self._ldx(self.memory.read_byte(addr))
                self.cycles += 4
            case 0xB0:
                # BCS rel
                self._branch(self.p & CARRY_FLAG)
            case 0xB6:
                # LDX zpg,y
                addr = self.read_pc_byte()
                self._ldx(self.memory.read_byte((addr + self.y) & 0xFF))
                self.cycles += 4
            case 0xB8:
                # CLV
                self.set_flag(OVERFLOW_FLAG, 0)

                self.cycles += 2
            case 0xBA:
                # TSX
                self.x = self.sp

                self.set_flag(ZERO_FLAG, self.sp == 0)
                self.set_flag(NEGATIVE_FLAG, self.sp & NEGATIVE_FLAG)
            case 0xBE:
                # LDX abs,y
                addr = self.read_pc_word()
                self._ldx(self.memory.read_byte(addr + self.y))
                self.cycles += 4

                if not page_of(addr) == page_of(addr + self.y):
                    self.cycles += 1
            case 0xC0:
                # CPY imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.y >= imm)
                self.set_flag(ZERO_FLAG, self.y == imm)
                self.set_flag(NEGATIVE_FLAG, (self.y - imm) & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xC8:
                # INY
                self.y = (self.y + 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xC9:
                # CMP imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.a >= imm)
                self.set_flag(ZERO_FLAG, self.a == imm)
                self.set_flag(NEGATIVE_FLAG, (self.a - imm) & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xCA:
                # DEX
                self.x = (self.x - 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xD0:
                # BNE rel
                self._branch(not self.p & ZERO_FLAG)
            case 0xD8:
                # CLD
                self.set_flag(DECIMAL_FLAG, 0)

                self.cycles += 2
            case 0xE0:
                # CPX imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.x >= imm)
                self.set_flag(ZERO_FLAG, self.x == imm)
                self.set_flag(NEGATIVE_FLAG, (self.x - imm) & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xEA:
                # NOP
                self.cycles += 2
            case 0xE8:
                # INX
                self.x = (self.x + 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xE9:
                # SBC imm
                imm = self.read_pc_byte()

                prev_a = self.a
                new_a = self.a + (~imm) + (self.p & CARRY_FLAG)
                self.a = new_a & 0xFF

                self.set_flag(CARRY_FLAG, not new_a < 0x00)
                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(
                    OVERFLOW_FLAG, (self.a ^ prev_a) & (self.a ^ (~imm)) & 0x80
                )
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                self.cycles += 2
            case 0xF0:
                # BEQ rel
                self._branch(self.p & ZERO_FLAG)
            case 0xF8:
                # SED
                self.set_flag(DECIMAL_FLAG, 1)

                self.cycles += 2
            case _:
                raise ValueError(f"unknown opcode: {hex(opcode)}")

        # TODO: check IRQ and handle interrupts
        if new_interrupts_state:
            self.set_flag(
                INTERRUPT_DISABLE_FLAG, 1 if new_interrupts_state == "disabled" else 0
            )

        return self.cycles
