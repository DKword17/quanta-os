#
# kernel/Makefile — Quanta OS 微核构建
# 输出: quanta_kernel.bin (≤64KB)
#

CC      = gcc
CFLAGS  = -Os -march=x86-64 -nostdlib -ffreestanding -fno-builtin -Wall -Werror
LDFLAGS = -T linker.ld -nostdlib -static
OBJS    = boot.o gate_discovery.o topology_mapper.o

.PHONY: all clean

all: quanta_kernel.bin

quanta_kernel.bin: quanta_kernel.elf
	objcopy -O binary $< $@
	@echo "Kernel size: $$(wc -c < $@) bytes"
	@if [ $$(wc -c < $@) -gt 65536 ]; then \
		echo "ERROR: Kernel exceeds 64KB limit!"; \
		exit 1; \
	fi

quanta_kernel.elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f *.o *.elf *.bin
