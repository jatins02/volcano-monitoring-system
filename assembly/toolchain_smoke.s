# Stage 1 ABI/toolchain check only; this is not the future sensor analyser.
.include "assembly/rules.inc"

.section .rodata
message: .string "AT&T assembly toolchain: OK"

.section .text
.globl main
.type main, @function
main:
        # System V entry RSP is 8 modulo 16. Saving RBP aligns the puts call.
        pushq %rbp
        movq %rsp, %rbp
        leaq message(%rip), %rdi
        call puts@PLT
        # Return the generated rule version minus one, so version 1 is success.
        movl $VM_RULE_VERSION, %eax
        subl $1, %eax
        popq %rbp
        ret
.size main, .-main

.section .note.GNU-stack,"",@progbits
