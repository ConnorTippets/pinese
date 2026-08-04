class CPUMemory:
    def __init__(self):
        # C808 bytes is the amount of actual bytes on the NES
        # the rest are mirrors that essentially pad out to 65536
        self.ram = bytearray(0xC808)

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

        raise ValueError(
            "Address passed to CPU read_byte must be in range 0x0000-0xFFFF"
        )

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

        raise ValueError(
            "Address passed to CPU read_word must be in range 0x0000-0xFFFF"
        )

    def write_byte(self, addr: int, value: int):
        if 0x0000 <= addr <= 0x1FFF:
            self.ram[addr % 0x0800] = value
            return
        if 0x2000 <= addr <= 0x3FFF:
            self.ram[((addr - 0x2000) % 8) + 0x0800] = value
            return
        if 0x4000 <= addr <= 0x4017:
            self.ram[addr - 0x4000 + 0x0808] = value
            return
        if 0x4018 <= addr <= 0x401F:
            self.ram[addr - 0x4018 + 0x0820] = value
            return
        if 0x4020 <= addr <= 0xFFFF:
            self.ram[addr - 0x4020 + 0x0828] = value
            return

        raise ValueError(
            "Address passed to CPU write_byte must be in range 0x0000-0xFFFF"
        )

    def write_word(self, addr: int, value: int):
        if 0x0000 <= addr <= 0x1FFF:
            self._raw_write_word(addr % 0x0800, value)
            return
        if 0x2000 <= addr <= 0x3FFF:
            self._raw_write_word(((addr - 0x2000) % 8) + 0x0800, value)
            return
        if 0x4000 <= addr <= 0x4017:
            self._raw_write_word(addr - 0x4000 + 0x0808, value)
            return
        if 0x4018 <= addr <= 0x401F:
            self._raw_write_word(addr - 0x4018 + 0x0820, value)
            return
        if 0x4020 <= addr <= 0xFFFF:
            self._raw_write_word(addr - 0x4020 + 0x0828, value)
            return

        raise ValueError(
            "Address passed to CPU write_word must be in range 0x0000-0xFFFF"
        )

    def _raw_read_word(self, addr: int) -> int:
        return (self.ram[addr + 1] << 8) | self.ram[addr]

    def _raw_write_word(self, addr: int, value: int):
        self.ram[addr] = value & 0xFF
        self.ram[addr + 1] = (value >> 8) & 0xFF


class PPUMemory:
    def __init__(self):
        self.ram = bytearray(0x3F20)

    def read_byte(self, addr: int) -> int:
        if 0x0000 <= addr <= 0x3F1F:
            return self.ram[addr]
        if 0x3F20 <= addr <= 0xFFFF:
            return self.ram[((addr - 0x3F20) % 32) + 0x3F00]

        raise ValueError(
            "Address passed to PPU read_byte must be in range 0x0000-0xFFFF"
        )

    def read_word(self, addr: int) -> int:
        if 0x0000 <= addr <= 0x3F1F:
            return self._raw_read_word(addr)
        if 0x3F20 <= addr <= 0xFFFF:
            return self._raw_read_word(((addr - 0x3F20) % 32) + 0x3F00)

        raise ValueError(
            "Address passed to PPU read_word must be in range 0x0000-0xFFFF"
        )

    def _raw_read_word(self, addr: int) -> int:
        return (self.ram[addr + 1] << 8) | self.ram[addr]
