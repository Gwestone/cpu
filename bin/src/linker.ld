ENTRY(_start)

MEMORY
{
  MEM (rwx) : ORIGIN = 0x00000000, LENGTH = 64M
}


SECTIONS
{
    . = ORIGIN(MEM);

  .text : { *(.text.start*) *(.text*) *(.rodata*) } > MEM
  .data : { *(.data*) } > MEM
  .bss : {
    . = ALIGN(8);
    _bss_start = .;
    *(.bss)
    *(SOURCE)
    . = ALIGN(8);
    _bss_end = .;
    } > MEM
}

_stack_top = ORIGIN(MEM) + LENGTH(MEM);
