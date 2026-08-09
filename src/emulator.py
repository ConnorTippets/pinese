import os

from .cpu import CPU
from .memory import CPUMemory, PPUMemory
from .util import sign_convert_byte

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

        self.disasm = ""
        self.length = 1
        self.undocumented = False

        self.total_cycles = 0

    def run(self, log=False):
        while True:
            if log:
                self.print_log_line()

            self.cpu.step()
            self.total_cycles += self.cpu.cycles

    def disasm_immediate(self, instruction: str, undocumented: bool = False):
        self.undocumented = undocumented
        imm = self.cpumemory.read_byte(self.cpu.pc + 1)
        self.disasm = f"{instruction} #${hex(imm).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_indirect_x(self, instruction: str):
        base = self.cpumemory.read_byte(self.cpu.pc + 1)
        addr = (
            self.cpumemory.read_byte((base + self.cpu.x) & 0xFF)
            + self.cpumemory.read_byte((base + self.cpu.x + 1) & 0xFF) * 256
        )
        self.disasm = f"{instruction} (${hex(base).upper().replace("0X", ""):>02},X) @ {hex((base + self.cpu.x) & 0xFF).upper().replace("0X", ""):>02} = {hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_indirect_y(self, instruction: str):
        base = self.cpumemory.read_byte(self.cpu.pc + 1)
        base_mutated = (
            self.cpumemory.read_byte(base)
            + self.cpumemory.read_byte((base + 1) & 0xFF) * 256
        )
        addr = (
            self.cpumemory.read_byte(base)
            + self.cpumemory.read_byte((base + 1) & 0xFF) * 256
            + self.cpu.y
        ) & 0xFFFF
        self.disasm = f"{instruction} (${hex(base).upper().replace("0X", ""):>02}),Y = {hex(base_mutated).upper().replace("0X", ""):>04} @ {hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_zpg(self, instruction: str, undocumented: bool = False):
        self.undocumented = undocumented
        addr = self.cpumemory.read_byte(self.cpu.pc + 1)
        self.disasm = f"{instruction} ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_zpg_x(self, instruction: str, undocumented: bool = False):
        self.undocumented = undocumented
        base = self.cpumemory.read_byte(self.cpu.pc + 1)
        addr = (base + self.cpu.x) & 0xFF
        self.disasm = f"{instruction} ${hex(base).upper().replace("0X", ""):>02},X @ {hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_zpg_y(self, instruction: str):
        base = self.cpumemory.read_byte(self.cpu.pc + 1)
        addr = (base + self.cpu.y) & 0xFF
        self.disasm = f"{instruction} ${hex(base).upper().replace("0X", ""):>02},Y @ {hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 2

    def disasm_implied(self, instruction: str, undocumented: bool = False):
        self.undocumented = undocumented
        self.disasm = instruction
        self.length = 1

    def disasm_accum(self, instruction: str):
        self.disasm = f"{instruction} A"
        self.length = 1

    def disasm_abs(
        self, instruction: str, show_contents: bool = False, undocumented: bool = False
    ):
        self.undocumented = undocumented
        addr = self.cpumemory.read_word(self.cpu.pc + 1)

        if show_contents:
            self.disasm = f"{instruction} ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        else:
            self.disasm = f"{instruction} ${hex(addr).upper().replace("0X", ""):>04}"

        self.length = 3

    def disasm_abs_x(self, instruction: str, undocumented: bool = False):
        self.undocumented = undocumented
        base = self.cpumemory.read_word(self.cpu.pc + 1)
        addr = (base + self.cpu.x) & 0xFFFF
        self.disasm = f"{instruction} ${hex(base).upper().replace("0X", ""):>04},X @ {hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 3

    def disasm_abs_y(self, instruction: str):
        base = self.cpumemory.read_word(self.cpu.pc + 1)
        addr = (base + self.cpu.y) & 0xFFFF
        self.disasm = f"{instruction} ${hex(base).upper().replace("0X", ""):>04},Y @ {hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
        self.length = 3

    def disasm_relative(self, instruction: str):
        rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
        addr = self.cpu.pc + 2 + rel
        self.disasm = f"{instruction} ${hex(addr).upper().replace("0X", ""):>04}"
        self.length = 2

    def disasm_indirect(self, instruction: str):
        base = self.cpumemory.read_word(self.cpu.pc + 1)

        # Theres a bug with JMP indirect where page boundaries are wrong
        if base & 0xFF == 0xFF:
            addr = self.cpumemory.read_byte(base) | (
                self.cpumemory.read_byte(base & 0xFF00) << 8
            )
        else:
            addr = self.cpumemory.read_word(base)

        self.disasm = f"{instruction} (${hex(base).upper().replace("0X", ""):>04}) = {hex(addr).upper().replace("0X", ""):>04}"
        self.length = 3

    def print_log_line(self):
        opcode = self.cpumemory.read_byte(self.cpu.pc)

        self.disasm = "UNKNOWN OPCODE"
        self.length = 3
        self.undocumented = False

        # fmt: off
        match opcode:
            case 0x00: self.disasm_immediate("BRK")
            case 0x01: self.disasm_indirect_x("ORA")
            case 0x05: self.disasm_zpg("ORA")
            case 0x06: self.disasm_zpg("ASL")
            case 0x08: self.disasm_implied("PHP")
            case 0x09: self.disasm_immediate("ORA")
            case 0x0A: self.disasm_accum("ASL")
            case 0x0D: self.disasm_abs("ORA", show_contents = True)
            case 0x0E: self.disasm_abs("ASL", show_contents = True)
            case 0x10: self.disasm_relative("BPL")
            case 0x11: self.disasm_indirect_y("ORA")
            case 0x15: self.disasm_zpg_x("ORA")
            case 0x16: self.disasm_zpg_x("ASL")
            case 0x18: self.disasm_implied("CLC")
            case 0x19: self.disasm_abs_y("ORA")
            case 0x1D: self.disasm_abs_x("ORA")
            case 0x1E: self.disasm_abs_x("ASL")
            case 0x20: self.disasm_abs("JSR")
            case 0x21: self.disasm_indirect_x("AND")
            case 0x24: self.disasm_zpg("BIT")
            case 0x25: self.disasm_zpg("AND")
            case 0x26: self.disasm_zpg("ROL")
            case 0x28: self.disasm_implied("PLP")
            case 0x29: self.disasm_immediate("AND")
            case 0x2A: self.disasm_accum("ROL")
            case 0x2C: self.disasm_abs("BIT", show_contents = True)
            case 0x2D: self.disasm_abs("AND", show_contents = True)
            case 0x2E: self.disasm_abs("ROL", show_contents = True)
            case 0x30: self.disasm_relative("BMI")
            case 0x31: self.disasm_indirect_y("AND")
            case 0x35: self.disasm_zpg_x("AND")
            case 0x36: self.disasm_zpg_x("ROL")
            case 0x38: self.disasm_implied("SEC")
            case 0x39: self.disasm_abs_y("AND")
            case 0x3D: self.disasm_abs_x("AND")
            case 0x3E: self.disasm_abs_x("ROL")
            case 0x40: self.disasm_implied("RTI")
            case 0x41: self.disasm_indirect_x("EOR")
            case 0x45: self.disasm_zpg("EOR")
            case 0x46: self.disasm_zpg("LSR")
            case 0x48: self.disasm_implied("PHA")
            case 0x49: self.disasm_immediate("EOR")
            case 0x4A: self.disasm_accum("LSR")
            case 0x4C: self.disasm_abs("JMP")
            case 0x4D: self.disasm_abs("EOR", show_contents = True)
            case 0x4E: self.disasm_abs("LSR", show_contents = True)
            case 0x50: self.disasm_relative("BVC")
            case 0x51: self.disasm_indirect_y("EOR")
            case 0x55: self.disasm_zpg_x("EOR")
            case 0x56: self.disasm_zpg_x("LSR")
            case 0x58: self.disasm_implied("CLI")
            case 0x59: self.disasm_abs_y("EOR")
            case 0x5D: self.disasm_abs_x("EOR")
            case 0x5E: self.disasm_abs_x("LSR")
            case 0x60: self.disasm_implied("RTS")
            case 0x61: self.disasm_indirect_x("ADC")
            case 0x65: self.disasm_zpg("ADC")
            case 0x66: self.disasm_zpg("ROR")
            case 0x68: self.disasm_implied("PLA")
            case 0x69: self.disasm_immediate("ADC")
            case 0x6A: self.disasm_accum("ROR")
            case 0x6C: self.disasm_indirect("JMP")
            case 0x6D: self.disasm_abs("ADC", show_contents = True)
            case 0x6E: self.disasm_abs("ROR", show_contents = True)
            case 0x70: self.disasm_relative("BVS")
            case 0x71: self.disasm_indirect_y("ADC")
            case 0x75: self.disasm_zpg_x("ADC")
            case 0x76: self.disasm_zpg_x("ROR")
            case 0x78: self.disasm_implied("SEI")
            case 0x79: self.disasm_abs_y("ADC")
            case 0x7D: self.disasm_abs_x("ADC")
            case 0x7E: self.disasm_abs_x("ROR")
            case 0x81: self.disasm_indirect_x("STA")
            case 0x84: self.disasm_zpg("STY")
            case 0x85: self.disasm_zpg("STA")
            case 0x86: self.disasm_zpg("STX")
            case 0x88: self.disasm_implied("DEY")
            case 0x8A: self.disasm_implied("TXA")
            case 0x8C: self.disasm_abs("STY", show_contents = True)
            case 0x8D: self.disasm_abs("STA", show_contents = True)
            case 0x8E: self.disasm_abs("STX", show_contents = True)
            case 0x90: self.disasm_relative("BCC")
            case 0x91: self.disasm_indirect_y("STA")
            case 0x94: self.disasm_zpg_x("STY")
            case 0x95: self.disasm_zpg_x("STA")
            case 0x96: self.disasm_zpg_y("STX")
            case 0x98: self.disasm_implied("TYA")
            case 0x99: self.disasm_abs_y("STA")
            case 0x9A: self.disasm_implied("TXS")
            case 0x9D: self.disasm_abs_x("STA")
            case 0xA0: self.disasm_immediate("LDY")
            case 0xA1: self.disasm_indirect_x("LDA")
            case 0xA2: self.disasm_immediate("LDX")
            case 0xA4: self.disasm_zpg("LDY")
            case 0xA5: self.disasm_zpg("LDA")
            case 0xA6: self.disasm_zpg("LDX")
            case 0xA8: self.disasm_implied("TAY")
            case 0xA9: self.disasm_immediate("LDA")
            case 0xAA: self.disasm_implied("TAX")
            case 0xAC: self.disasm_abs("LDY", show_contents = True)
            case 0xAD: self.disasm_abs("LDA", show_contents = True)
            case 0xAE: self.disasm_abs("LDX", show_contents = True)
            case 0xB0: self.disasm_relative("BCS")
            case 0xB1: self.disasm_indirect_y("LDA")
            case 0xB4: self.disasm_zpg_x("LDY")
            case 0xB5: self.disasm_zpg_x("LDA")
            case 0xB6: self.disasm_zpg_y("LDX")
            case 0xB8: self.disasm_implied("CLV")
            case 0xB9: self.disasm_abs_y("LDA")
            case 0xBA: self.disasm_implied("TSX")
            case 0xBC: self.disasm_abs_x("LDY")
            case 0xBD: self.disasm_abs_x("LDA")
            case 0xBE: self.disasm_abs_y("LDX")
            case 0xC0: self.disasm_immediate("CPY")
            case 0xC1: self.disasm_indirect_x("CMP")
            case 0xC4: self.disasm_zpg("CPY")
            case 0xC5: self.disasm_zpg("CMP")
            case 0xC6: self.disasm_zpg("DEC")
            case 0xC8: self.disasm_implied("INY")
            case 0xC9: self.disasm_immediate("CMP")
            case 0xCA: self.disasm_implied("DEX")
            case 0xCC: self.disasm_abs("CPY", show_contents = True)
            case 0xCD: self.disasm_abs("CMP", show_contents = True)
            case 0xCE: self.disasm_abs("DEC", show_contents = True)
            case 0xD0: self.disasm_relative("BNE")
            case 0xD1: self.disasm_indirect_y("CMP")
            case 0xD5: self.disasm_zpg_x("CMP")
            case 0xD6: self.disasm_zpg_x("DEC")
            case 0xD8: self.disasm_implied("CLD")
            case 0xD9: self.disasm_abs_y("CMP")
            case 0xDD: self.disasm_abs_x("CMP")
            case 0xDE: self.disasm_abs_x("DEC")
            case 0xE0: self.disasm_immediate("CPX")
            case 0xE1: self.disasm_indirect_x("SBC")
            case 0xE4: self.disasm_zpg("CPX")
            case 0xE5: self.disasm_zpg("SBC")
            case 0xE6: self.disasm_zpg("INC")
            case 0xE8: self.disasm_implied("INX")
            case 0xE9: self.disasm_immediate("SBC")
            case 0xEA: self.disasm_implied("NOP")
            case 0xEC: self.disasm_abs("CPX", show_contents = True)
            case 0xED: self.disasm_abs("SBC", show_contents = True)
            case 0xEE: self.disasm_abs("INC", show_contents = True)
            case 0xF0: self.disasm_relative("BEQ")
            case 0xF1: self.disasm_indirect_y("SBC")
            case 0xF5: self.disasm_zpg_x("SBC")
            case 0xF6: self.disasm_zpg_x("INC")
            case 0xF8: self.disasm_implied("SED")
            case 0xF9: self.disasm_abs_y("SBC")
            case 0xFD: self.disasm_abs_x("SBC")
            case 0xFE: self.disasm_abs_x("INC")
            
            case 0x1A | 0x3A | 0x7A | 0xDA | 0x5A | 0xFA: self.disasm_implied("NOP", undocumented = True)
            case 0x80 | 0x82 | 0x89 | 0xC2 | 0xE2: self.disasm_immediate("NOP", undocumented = True)
            case 0x0C: self.disasm_abs("NOP", show_contents = True, undocumented = True)
            case 0x1C | 0x3C | 0x5C | 0x7C | 0xDC | 0xFC: self.disasm_abs_x("NOP", undocumented = True)
            case 0x04 | 0x44 | 0x64: self.disasm_zpg("NOP", undocumented = True)
            case 0x14 | 0x34 | 0x54 | 0x74 | 0xD4 | 0xF4: self.disasm_zpg_x("NOP", undocumented = True)
        # fmt: on

        mem_bytes = " "
        for byte in range(self.length):
            mem_bytes = (
                mem_bytes
                + hex(self.cpumemory.read_byte(self.cpu.pc + byte))
                .upper()
                .replace("0X", "")
                .zfill(2)
                + " "
            )

        mem_bytes = mem_bytes.ljust(10)

        disasm = self.disasm.ljust(32)

        a_out = f"A:{hex(self.cpu.a).upper().replace("0X", ""):>02}"
        x_out = f"X:{hex(self.cpu.x).upper().replace("0X", ""):>02}"
        y_out = f"Y:{hex(self.cpu.y).upper().replace("0X", ""):>02}"
        p_out = f"P:{hex(self.cpu.p).upper().replace("0X", ""):>02}"
        sp_out = f"SP:{hex(self.cpu.sp).upper().replace("0X", ""):>02}"
        print(
            f"{hex(self.cpu.pc).upper().replace("0X", ""):>04} {mem_bytes}{"*" if self.undocumented else " "}{disasm}{a_out} {x_out} {y_out} {p_out} {sp_out}"
        )

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
