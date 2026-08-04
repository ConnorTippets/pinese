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

    def step(self) -> int:
        opcode = self.read_pc_byte()
        cycles = 0

        match opcode:
            case 0x4C:
                # JMP abs
                location = self.read_pc_word()

                self.pc = location
                cycles += 3
            case 0xA2:
                # LDX imm
                imm = self.read_pc_byte()

                self.x = imm
                self.set_flag(ZERO_FLAG, self.x == 0)
                self.set_flag(NEGATIVE_FLAG, self.x & NEGATIVE_FLAG)

                cycles += 2
            case _:
                raise ValueError(f"unknown opcode: {hex(opcode)}")

        return cycles
