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

    def run(self, log=False):
        while True:
            if log:
                self.print_log_line()

            self.cpu.step()

    def print_log_line(self):
        opcode = self.cpumemory.read_byte(self.cpu.pc)

        length = 1
        disasm = ""
        match opcode:
            case 0x08:
                # PHP
                disasm = "PHP"
            case 0x09:
                # ORA
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"ORA #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0x0A:
                # ASL a
                disasm = "ASL A"
            case 0x10:
                # BPL rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BPL ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0x18:
                # CLC
                disasm = "CLC"
            case 0x20:
                # JSR abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"JSR ${hex(addr).upper().replace("0X", ""):>04}"
                length = 3
            case 0x24:
                # BIT zpg
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"BIT ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0x28:
                # PLP
                disasm = "PLP"
            case 0x29:
                # AND imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"AND #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0x2A:
                # ROL a
                disasm = "ROL A"
            case 0x2C:
                # BIT abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"BIT ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0x30:
                # BMI rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BMI ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0x38:
                # SEC
                disasm = "SEC"
            case 0x40:
                # RTI
                disasm = "RTI"
            case 0x48:
                # PHA
                disasm = "PHA"
            case 0x49:
                # EOR
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"EOR #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0x4A:
                # LSR a
                disasm = "LSR A"
            case 0x4C:
                # JMP abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"JMP ${hex(addr).upper().replace("0X", ""):>04}"
                length = 3
            case 0x50:
                # BVC rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BVC ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0x60:
                # RTS
                disasm = "RTS"
            case 0x68:
                # PLA
                disasm = "PLA"
            case 0x69:
                # ADC imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"ADC #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0x6A:
                # ROR a
                disasm = "ROR A"
            case 0x70:
                # BVS rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BVS ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0x78:
                # SEI
                disasm = "SEI"
            case 0x85:
                # STA zpg
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"STA ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0x86:
                # STX zpg
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"STX ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0x88:
                # DEY
                disasm = "DEY"
            case 0x8A:
                # TXA
                disasm = "TXA"
            case 0x8D:
                # STA abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"STA ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 3
            case 0x8E:
                # STX abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"STX ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 3
            case 0x90:
                # BCS rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BCC ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0x96:
                # STX zpg,y
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"STX ${hex(addr).upper().replace("0X", ""):>02},Y = {hex(self.cpumemory.read_byte((addr+self.cpu.y) & 0xFF)).upper().replace("0X", ""):>02}"
                length = 2
            case 0x98:
                # TYA
                disasm = "TYA"
            case 0x9A:
                # TXS
                disasm = "TXS"
            case 0xA0:
                # LDY imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDY #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xA1:
                # LDA (indirect,x)
                base = self.cpumemory.read_byte(self.cpu.pc + 1)
                addr = (
                    self.cpumemory.read_byte((base + self.cpu.x) & 0xFF)
                    + self.cpumemory.read_byte((base + self.cpu.x + 1) & 0xFF) * 256
                )
                disasm = f"LDA (${hex(base).upper().replace("0X", ""):>02},X) @ {hex((base + self.cpu.x) & 0xFF).upper().replace("0X", ""):>02} = {hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0xA2:
                # LDX imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDX #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xA5:
                # LDA zpg
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDA ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0xA6:
                # LDX zpg
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDX ${hex(addr).upper().replace("0X", ""):>02} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 2
            case 0xA8:
                # TAY
                disasm = "TAY"
            case 0xA9:
                # LDA imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDA #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xAA:
                # TAX
                disasm = "TAX"
            case 0xAD:
                # LDA abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"LDA ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 3
            case 0xAE:
                # LDX abs
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"LDX ${hex(addr).upper().replace("0X", ""):>04} = {hex(self.cpumemory.read_byte(addr)).upper().replace("0X", ""):>02}"
                length = 3
            case 0xB0:
                # BCS rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BCS ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0xB6:
                # LDX zpg,y
                addr = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"LDX ${hex(addr).upper().replace("0X", ""):>02},Y = {hex(self.cpumemory.read_byte((addr+self.cpu.y) & 0xFF)).upper().replace("0X", ""):>02}"
                length = 2
            case 0xB8:
                # CLV
                disasm = "CLV"
            case 0xBA:
                # TSX
                disasm = "TSX"
            case 0xBE:
                # LDX abs,y
                addr = self.cpumemory.read_word(self.cpu.pc + 1)
                disasm = f"LDX ${hex(addr).upper().replace("0X", ""):>04},Y = {hex(self.cpumemory.read_byte((addr+self.cpu.y) & 0xFF)).upper().replace("0X", ""):>02}"
                length = 3
            case 0xC0:
                # CPY imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"CPY #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xC8:
                # INY
                disasm = "INY"
            case 0xC9:
                # CMP imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"CMP #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xCA:
                # DEX
                disasm = "DEX"
            case 0xD0:
                # BNE rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BNE ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0xD8:
                # CLD
                disasm = "CLD"
            case 0xE0:
                # CPX
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"CPX #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xEA:
                # NOP
                disasm = "NOP"
            case 0xE8:
                # INX
                disasm = "INX"
            case 0xE9:
                # SBC imm
                imm = self.cpumemory.read_byte(self.cpu.pc + 1)
                disasm = f"SBC #${hex(imm).upper().replace("0X", ""):>02}"
                length = 2
            case 0xF0:
                # BEQ rel
                rel = sign_convert_byte(self.cpumemory.read_byte(self.cpu.pc + 1))
                addr = self.cpu.pc + 2 + rel
                disasm = f"BEQ ${hex(addr).upper().replace("0X", ""):>04}"
                length = 2
            case 0xF8:
                # SED
                disasm = "SED"
            case _:
                length = 3
                disasm = "UNKNOWN OPCODE"

        mem_bytes = " "
        for byte in range(length):
            mem_bytes = (
                mem_bytes
                + hex(self.cpumemory.read_byte(self.cpu.pc + byte))
                .upper()
                .replace("0X", "")
                .zfill(2)
                + " "
            )

        mem_bytes = mem_bytes.ljust(10)

        disasm = disasm.ljust(32)

        a_out = f"A:{hex(self.cpu.a).upper().replace("0X", ""):>02}"
        x_out = f"X:{hex(self.cpu.x).upper().replace("0X", ""):>02}"
        y_out = f"Y:{hex(self.cpu.y).upper().replace("0X", ""):>02}"
        p_out = f"P:{hex(self.cpu.p).upper().replace("0X", ""):>02}"
        sp_out = f"SP:{hex(self.cpu.sp).upper().replace("0X", ""):>02}"
        print(
            f"{hex(self.cpu.pc).upper().replace("0X", ""):>04} {mem_bytes} {disasm}{a_out} {x_out} {y_out} {p_out} {sp_out}"
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
