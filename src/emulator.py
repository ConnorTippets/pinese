from .cpu import CPU
from .memory import Memory


class Emulator:
    def __init__(self, game_rom: str):
        self.memory = Memory()
        self.memory.load_game_rom(game_rom)

        self.cpu = CPU()
        self.cpu.memory = self.memory
        self.cpu.reset()

    def run(self):
        while True:
            self.cpu.step()
