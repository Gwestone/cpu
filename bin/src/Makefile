build:
	riscv64-unknown-elf-gcc -march=rv64i -mabi=lp64 -nostartfiles -nostdlib main.c start.s -T linker.ld -o firmware.elf

extract: build
	riscv64-unknown-elf-objcopy -O binary firmware.elf firmware.bin

clean:
	rm -f firmware.bin firmware.elf
