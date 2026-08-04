import os

NES_MAGIC_BYTES = b"NES\x1a"


# TODO: 0x8000 to 0xFFFF is read only
class Memory:
    def __init__(self):
        # 51208 bytes is the amount of actual bytes on the NES
        # the rest are mirrors that essentially pad out to 65536
        self.ram = bytearray(51208)

    def read_byte(self, addr: int) -> int:
        if 0x0000 <= addr <= 0x1FFF:
            return self.ram[addr % 0x0800]
        if 0x2000 <= addr <= 0x3FFF:
            return self.ram[((addr - 0x2000) % 8) + 0x0800]
        if 0x4000 <= addr <= 0x4017:
            return self.ram[addr - 0x4000 + 0x0808]
        if 0x4018 <= addr <= 0x401F:
            return self.ram[addr - 0x4018 + 0x0820]
        if 0x4020 <= addr <= 0xFFFF:
            return self.ram[addr - 0x4020 + 0x0828]

        raise ValueError("Address passed to read_byte must be in range 0x0000-0xFFFF")

    def read_word(self, addr: int) -> int:
        if 0x0000 <= addr <= 0x1FFF:
            return self._raw_read_word(addr % 0x0800)
        if 0x2000 <= addr <= 0x3FFF:
            return self._raw_read_word(((addr - 0x2000) % 8) + 0x0800)
        if 0x4000 <= addr <= 0x4017:
            return self._raw_read_word(addr - 0x4000 + 0x0808)
        if 0x4018 <= addr <= 0x401F:
            return self._raw_read_word(addr - 0x4018 + 0x0820)
        if 0x4020 <= addr <= 0xFFFF:
            return self._raw_read_word(addr - 0x4020 + 0x0828)

        raise ValueError("Address passed to read_word must be in range 0x0000-0xFFFF")

    def _raw_read_word(self, addr: int) -> int:
        return self.ram[addr] << 8 | self.ram[addr + 1]

    def load_game_rom(self, path: str):
        if os.path.getsize(path) < 16:
            raise ValueError("Invalid game rom: must be at least 16 bytes")

        contents = b""
        with open(path, "rb") as handle:
            contents = handle.read()

        if not contents[0:4] == NES_MAGIC_BYTES:
            raise ValueError("Invalid game rom: must contain .nes magic bytes")

        prog_size = contents[4]
        chr_size = contents[5]

        # TODO: this is more difficult than i expected
