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

    def step(self) -> int:
        opcode = self.read_pc_byte()
        cycles = 0

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

                cycles += 6
            case 0x05:
                # ORA zpg
                self._ora(self.memory.read_byte(self.read_pc_byte()))

                cycles += 3
            case 0x08:
                # PHP
                self.push_byte(self.p | B_FLAG)

                cycles += 3
            case 0x09:
                # ORA imm
                self._ora(self.read_pc_byte())

                cycles += 2
            case 0x0D:
                # ORA abs
                self._ora(self.memory.read_byte(self.read_pc_word()))

                cycles += 4
            case 0x10:
                # BPL rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if not self.p & NEGATIVE_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0x11:
                # ORA (indirect),y
                addr = self.read_pc_byte()
                base = (
                    self.memory.read_byte(addr)
                    + self.memory.read_byte((addr + 1) & 0xFF) * 256
                )
                self._ora(self.memory.read_byte(base + self.y))

                cycles += 5

                if not page_of(base) == page_of(base + self.y):
                    cycles += 1
            case 0x15:
                # ORA zpg,x
                self._ora(self.memory.read_byte((self.read_pc_byte() + self.x) & 0xFF))

                cycles += 4
            case 0x18:
                # CLC
                self.set_flag(CARRY_FLAG, 0)

                cycles += 2
            case 0x19:
                # ORA abs,y
                addr = self.read_pc_word()
                self._ora(self.memory.read_byte(addr + self.y))

                cycles += 4

                if not page_of(addr) == page_of(self.y):
                    cycles += 1
            case 0x1D:
                # ORA abs,x
                addr = self.read_pc_word()
                self._ora(self.memory.read_byte(addr + self.x))

                cycles += 4

                if not page_of(addr) == page_of(self.x):
                    cycles += 1
            case 0x20:
                # JSR abs
                location = self.read_pc_word()
                self.push_word(self.pc)

                self.pc = location
                cycles += 6
            case 0x24:
                # BIT zpg
                addr = self.read_pc_byte()
                val = self.memory.read_byte(addr)

                self.set_flag(ZERO_FLAG, (self.a & val) == 0)
                self.set_flag(OVERFLOW_FLAG, val & OVERFLOW_FLAG)
                self.set_flag(NEGATIVE_FLAG, val & NEGATIVE_FLAG)

                cycles += 3
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

                cycles += 4

            case 0x29:
                # AND imm
                imm = self.read_pc_byte()
                self.a &= imm

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 2
            case 0x30:
                # BMI rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if self.p & NEGATIVE_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0x38:
                # SEC
                self.set_flag(CARRY_FLAG, 1)

                cycles += 2
            case 0x48:
                # PHA
                self.push_byte(self.a)

                cycles += 3
            case 0x49:
                # EOR
                imm = self.read_pc_byte()
                self.a ^= imm

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 2
            case 0x50:
                # BVC rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if not self.p & OVERFLOW_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0x60:
                # RTS
                self.pc = self.pop_word()
            case 0x68:
                # PLA
                self.a = self.pop_byte()

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 4
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

                cycles += 2
            case 0x70:
                # BVS rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if self.p & OVERFLOW_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0x78:
                # SEI
                new_interrupts_state = "disabled"
            case 0x4C:
                # JMP abs
                location = self.read_pc_word()

                self.pc = location
                cycles += 3
            case 0x85:
                # STA zpg
                addr = self.read_pc_byte()

                self.memory.write_byte(addr, self.a)
                cycles += 3
            case 0x86:
                # STX zpg
                addr = self.read_pc_byte()

                self.memory.write_byte(addr, self.x)
                cycles += 3
            case 0x88:
                # DEY
                self.y = (self.y - 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                cycles += 2
            case 0x90:
                # BCC rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if not self.p & CARRY_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0xA0:
                # LDY imm
                imm = self.read_pc_byte()

                self.y = imm
                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                cycles += 2
            case 0xA2:
                # LDX imm
                imm = self.read_pc_byte()

                self.x = imm
                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                cycles += 2
            case 0xA8:
                # TAY
                self.y = self.a

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 2
            case 0xA9:
                # LDA imm
                imm = self.read_pc_byte()

                self.a = imm
                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 2
            case 0xAA:
                # TAX
                self.x = self.a

                self.set_flag(ZERO_FLAG, self.a == 0)
                self.set_flag(NEGATIVE_FLAG, self.a & NEGATIVE_FLAG)

                cycles += 2
            case 0xB0:
                # BCS rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if self.p & CARRY_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0xB8:
                # CLV
                self.set_flag(OVERFLOW_FLAG, 0)

                cycles += 2
            case 0xC0:
                # CPY imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.y >= imm)
                self.set_flag(ZERO_FLAG, self.y == imm)
                self.set_flag(NEGATIVE_FLAG, (self.y - imm) & NEGATIVE_FLAG)

                cycles += 2
            case 0xC8:
                # INY
                self.y = (self.y + 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.y == 0)
                self.set_flag(NEGATIVE_FLAG, self.y & NEGATIVE_FLAG)

                cycles += 2
            case 0xC9:
                # CMP imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.a >= imm)
                self.set_flag(ZERO_FLAG, self.a == imm)
                self.set_flag(NEGATIVE_FLAG, (self.a - imm) & NEGATIVE_FLAG)

                cycles += 2
            case 0xCA:
                # DEX
                self.x = (self.x - 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                cycles += 2
            case 0xD0:
                # BNE rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if not self.p & ZERO_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0xD8:
                # CLD
                self.set_flag(DECIMAL_FLAG, 0)

                cycles += 2
            case 0xE0:
                # CPX imm
                imm = self.read_pc_byte()

                self.set_flag(CARRY_FLAG, self.x >= imm)
                self.set_flag(ZERO_FLAG, self.x == imm)
                self.set_flag(NEGATIVE_FLAG, (self.x - imm) & NEGATIVE_FLAG)

                cycles += 2
            case 0xEA:
                # NOP
                cycles += 2
            case 0xE8:
                # INX
                self.x = (self.x + 1) & 0xFF

                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                cycles += 2
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

                cycles += 2
            case 0xF0:
                # BEQ rel
                rel = sign_convert_byte(self.read_pc_byte())

                cycles += 2

                if self.p & ZERO_FLAG:
                    self.pc += rel  # + 2 was handled already

                    cycles += 1

                    # page boundary crossed
                    if not page_of(self.pc - rel) == page_of(self.pc):
                        cycles += 1
            case 0xF8:
                # SED
                self.set_flag(DECIMAL_FLAG, 1)

                cycles += 2
            case _:
                raise ValueError(f"unknown opcode: {hex(opcode)}")

        # TODO: check IRQ and handle interrupts
        if new_interrupts_state:
            self.set_flag(
                INTERRUPT_DISABLE_FLAG, 1 if new_interrupts_state == "disabled" else 0
            )

        return cycles
