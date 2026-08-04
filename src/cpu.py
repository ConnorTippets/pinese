from .memory import CPUMemory, PPUMemory


class CPU:
    def __init__(self):
        self.memory: CPUMemory
        self.ppumemory: PPUMemory

    def reset(self):
        self.pc = self.memory.read_word(0xFFFC)

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
