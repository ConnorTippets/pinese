from .memory import Memory


class CPU:
    def __init__(self):
        self.memory: Memory

    def reset(self):
        self.pc = self.memory.read_word(0xFFFC)

    def step(self):
        opcode = self.memory.read_byte(self.pc)

        print(opcode)
