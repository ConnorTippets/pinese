import sys
import time

from src.emulator import Emulator


def main(game_rom: str):
    emu = Emulator(game_rom)

    s = time.perf_counter()
    try:
        emu.run(log=True)
    finally:
        e = time.perf_counter()
        print(f"{e-s=}", file=sys.stderr)
        print(f"{emu.total_cycles=}", file=sys.stderr)

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
