import os

from .cpu import CPU
from .memory import CPUMemory, PPUMemory

NES_MAGIC_BYTES = b"NES\x1a"


class Emulator:
    def __init__(self, game_rom: str):
        self.cpumemory = CPUMemory()
        self.ppumemory = PPUMemory()

        self.load_game_rom(game_rom)

        self.cpu = CPU()
        self.cpu.memory = self.cpumemory
        self.cpu.ppumemory = self.ppumemory  # change this to a better name?
        self.cpu.reset()

    def run(self):
        while True:
            self.cpu.step()

    def load_game_rom(self, path: str):
        if os.path.getsize(path) < 16:
            raise ValueError("Invalid game rom: must be at least 16 bytes")

        contents = b""
        with open(path, "rb") as handle:
            contents = handle.read()

        if not contents[0:4] == NES_MAGIC_BYTES:
            raise ValueError("Invalid game rom: must contain .nes magic bytes")

        prog_size = contents[4]
        prog_size_bytes = 16384 * prog_size

        chr_size = contents[5]
        chr_size_bytes = 8192 * chr_size
        chr_start = 16 + prog_size_bytes

        prog_rom = contents[16 : 16 + prog_size_bytes]
        chr_rom = contents[chr_start : chr_start + chr_size_bytes]

        mapper = (contents[6] >> 4) | (contents[7] & 0xF0)
        if not mapper == 0:
            raise ValueError("Invalid game rom: only mapper 0 is supported")

        first_bank = prog_rom[:16384]
        second_bank = prog_rom[16384:]

        self.cpumemory.ram[0x4808:0x8808] = first_bank

        if second_bank:
            self.cpumemory.ram[0x8808:] = second_bank
        else:
            self.cpumemory.ram[0x8808:] = first_bank

        self.ppumemory.ram[0x0000:0x2000] = chr_rom
