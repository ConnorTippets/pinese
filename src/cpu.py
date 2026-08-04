from .memory import CPUMemory, PPUMemory


class CPU:
    def __init__(self):
        self.memory: CPUMemory
        self.ppumemory: PPUMemory

    def reset(self):
        self.pc = self.memory.read_word(0xFFFC)

    def step(self):
        opcode = self.memory.read_byte(self.pc)

        # match opcode:
        #     case 0x4C:
        #         # JMP abs
        #
        #     case _:
        #         raise ValueError(f"unknown opcode: {hex(opcode)}")
        # print(hex(opcode))
