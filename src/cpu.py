from .memory import CPUMemory, PPUMemory

INTERRUPT_DISABLE = 0b00000100


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

        self.p |= INTERRUPT_DISABLE

    def step(self) -> int:
        opcode = self.memory.read_byte(self.pc)
        cycles = 0

        self.pc += 1

        match opcode:
            case 0x4C:
                # JMP abs
                location = self.memory.read_word(self.pc)
                self.pc += 2

                self.pc = location
                cycles += 3
            case _:
                raise ValueError(f"unknown opcode: {hex(opcode)}")

        return cycles
