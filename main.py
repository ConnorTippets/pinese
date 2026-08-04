import sys

from src.emulator import Emulator


def main(game_rom: str):
    emu = Emulator(game_rom)
    emu.run()

    return

    # Code below dumps entire memory
    memory = []
    for i in range(0x10000):
        memory.append(emu.cpumemory.read_byte(i))

    memory = bytes(memory)

    with open("out.bin", "wb") as f:
        f.write(memory)


if __name__ == "__main__":
    main(sys.argv[1])
