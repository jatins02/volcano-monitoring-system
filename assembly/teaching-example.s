# Teaching example: classify one reading. Not used by the application.
.include "assembly/rules.inc"

.text
.globl classify_reading
.type classify_reading, @function
# RDI: four unsigned 32-bit values (V,T,G,A).
# ESI: connectivity (15 = all connected).
# EAX: 0=NORMAL, 1=WATCH, 2=DANGER, 3=FAULT.
# EDX: K, abnormal sensor count; zero on FAULT.
# Leaf function: caller-saved registers, no stack.
classify_reading:
    xorl %edx, %edx
    cmpl $VM_CONNECTED_MASK, %esi
    jne fault

    # Check every value before counting any abnormal sensors.
    xorl %ecx, %ecx
check_values:
    cmpl $VM_INPUT_MAX, (%rdi,%rcx,4)
    ja fault
    incq %rcx
    cmpq $4, %rcx
    jne check_values

    leaq thresholds(%rip), %r8
    xorl %ecx, %ecx
count_abnormal:
    movl (%rdi,%rcx,4), %eax
    cmpl (%r8,%rcx,4), %eax
    jbe next_sensor                 # Equal to the threshold is OFF.
    incl %edx
next_sensor:
    incq %rcx
    cmpq $4, %rcx
    jne count_abnormal

    movl $VM_WARNING_NORMAL, %eax
    testl %edx, %edx
    jz done
    movl $VM_WARNING_WATCH, %eax
    cmpl $1, %edx
    je done
    movl $VM_WARNING_DANGER, %eax
    ret
fault:
    movl $VM_WARNING_FAULT, %eax
done:
    ret
.size classify_reading, .-classify_reading

.section .rodata
thresholds:
    .long VM_THRESHOLD_V, VM_THRESHOLD_T
    .long VM_THRESHOLD_G, VM_THRESHOLD_A

.section .note.GNU-stack,"",@progbits
