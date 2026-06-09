# start.s — runs before main()
.section .text.start
.global _start
_start:
    # set stack pointer to top of memory
    la   sp, _stack_top

    # zero out BSS section
    la   t0, _bss_start
    la   t1, _bss_end
bss_loop:
    beq  t0, t1, bss_done
    sd   zero, 0(t0)
    addi t0, t0, 8
    j    bss_loop
bss_done:

    # call main
    call main

    # if main returns, halt
halt:
    j halt
