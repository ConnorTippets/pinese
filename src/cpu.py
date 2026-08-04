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

    def step(self) -> int:
        opcode = self.read_pc_byte()
        cycles = 0

        should_disable_interrupts = False
        match opcode:
            case 0x18:
                # CLC
                self.set_flag(CARRY_FLAG, 0)

                cycles += 2
            case 0x20:
                # JSR abs
                location = self.read_pc_word()
                self.push_word(self.pc)

                self.pc = location
                cycles += 6
            case 0x38:
                # SEC
                self.set_flag(CARRY_FLAG, 1)

                cycles += 2
            case 0x78:
                # SEI
                should_disable_interrupts = True
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
            case 0xA2:
                # LDX imm
                imm = self.read_pc_byte()

                self.x = imm
                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                cycles += 2
            case 0xA9:
                # LDA imm
                imm = self.read_pc_byte()

                self.a = imm
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
            case 0xEA:
                # NOP
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
        if should_disable_interrupts:
            self.set_flag(INTERRUPT_DISABLE_FLAG, 1)

        return cycles
