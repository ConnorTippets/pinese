import sys

from src.emulator import Emulator


def main(game_rom: str):
    emu = Emulator(game_rom)
    emu.run()

    open()


if __name__ == "__main__":
    main(sys.argv[1])
