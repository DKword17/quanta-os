/*
 * kernel/linker.ld — 独立微核链接脚本
 * 目标：输出平坦二进制，入口在 0x1000
 */

OUTPUT_FORMAT("elf64-x86-64")
ENTRY(quanta_os_main)

SECTIONS
{
    . = 0x1000;
    
    .text : {
        *(.text*)
    }
    
    .rodata : {
        *(.rodata*)
    }
    
    .data : {
        *(.data*)
    }
    
    .bss : {
        *(.bss*)
    }
}
