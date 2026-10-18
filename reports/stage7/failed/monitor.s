# Version-1 standalone binary analyser, System V AMD64, GNU AT&T syntax.
# Input is fully validated before any successful machine-readable output.
.include "assembly/rules.inc"

.section .rodata
thresholds: .long VM_THRESHOLD_V, VM_THRESHOLD_T, VM_THRESHOLD_G, VM_THRESHOLD_A
counter_shifts: .long 0, 4, 8, 12, 16, 22, 26
sensor_names: .ascii "VTGA"
header_text: .string "VMASM 1"
row_format: .string "R %u %u %u %u %u %u\n"
stat_format: .string "S %c %u %lu %lu %lu %lu\n"
empty_format: .string "S_EMPTY %c\n"
summary_format: .string "SUMMARY %u %u %u %d %d\n"
end_format: .string "END %u\n"
average_format: .string "REPORT AVERAGE %c %lu.%02lu\n"
report_format: .string "REPORT STATUS %s\n"
normal_text: .string "NORMAL"
watch_text: .string "WATCH"
danger_text: .string "DANGER"
no_data_text: .string "NO_VALID_DATA"
input_error: .string "Invalid version-1 input stream\n"
output_error: .string "Native analyser I/O failure\n"

.section .bss
.balign 8
input_header: .zero 16
input_rows: .zero 14400
current_counts: .zero 28
completed_counts: .zero 28
position: .zero 4
sequence: .zero 4
valid_count: .zero 4
fault_count: .zero 4
bus3: .zero 4
.balign 8
sums: .zero 32
minima: .zero 32
maxima: .zero 32

.section .data
last_warning: .long -1
worst_warning: .long -1

.section .text
.globl main
.type main,@function
main:
        # R12=index, R13=N, RBX=row pointer; R14=B2, R15=B1.
        # Six saved registers plus eight bytes keep RSP 16-byte aligned at calls.
        pushq %rbp
        movq %rsp, %rbp
        pushq %rbx
        pushq %r12
        pushq %r13
        pushq %r14
        pushq %r15
        subq $8, %rsp
        leaq input_header(%rip), %rdi
        movl $1, %esi
        movl $16, %edx
        movq stdin(%rip), %rcx
        call fread@PLT
        cmpq $16, %rax
        jne .Lshort_input
        cmpl $VM_ASSEMBLY_MAGIC, input_header(%rip)
        jne .Lbad_input
        cmpl $VM_PROTOCOL_VERSION, input_header+4(%rip)
        jne .Lbad_input
        cmpl $VM_RULE_VERSION, input_header+12(%rip)
        jne .Lbad_input
        movl input_header+8(%rip), %r13d
        cmpl $VM_MAX_SAMPLES, %r13d
        ja .Lbad_input
        leaq input_rows(%rip), %rdi
        movl $1, %esi
        imull $24, %r13d, %edx
        movq stdin(%rip), %rcx
        call fread@PLT
        imull $24, %r13d, %edx
        cmpq %rdx, %rax
        jne .Lshort_input
        movq stdin(%rip), %rdi
        call fgetc@PLT
        cmpl $-1, %eax
        jne .Lbad_input
        movq stdin(%rip), %rdi
        call ferror@PLT
        testl %eax, %eax
        jne .Lio_error
        xorl %r12d, %r12d
        leaq input_rows(%rip), %rbx
.Lvalidate_row:
        cmpl %r13d, %r12d
        jae .Lvalidated
        cmpl %r12d, (%rbx)
        jne .Lbad_input
        cmpl $15, 20(%rbx)
        ja .Lbad_input
        xorl %ecx, %ecx
.Lvalidate_sensor:
        cmpl $VM_TRANSPORT_MAX, 4(%rbx,%rcx,4)
        ja .Lbad_input
        incl %ecx
        cmpl $4, %ecx
        jb .Lvalidate_sensor
        incl %r12d
        addq $24, %rbx
        jmp .Lvalidate_row
.Lvalidated:
        jmp .Lbad_input
        leaq header_text(%rip), %rdi
        call puts@PLT
        testl %eax, %eax
        js .Lio_error
        xorl %r12d, %r12d
        leaq input_rows(%rip), %rbx
.Lrow:
        cmpl %r13d, %r12d
        jae .Lstatistics
        movq %rbx, %rdi
        call .Lclassify
        movl %eax, %r14d
        movl %edx, %r15d
        testl $0x8000, %r14d
        jnz .Lfault
        incl valid_count(%rip)
        movl %r14d, %eax
        shrl $12, %eax
        andl $3, %eax
        movl %eax, last_warning(%rip)
        cmpl worst_warning(%rip), %eax
        jle .Lstats_update
        movl %eax, worst_warning(%rip)
.Lstats_update:
        xorl %ecx, %ecx
        leaq sums(%rip), %rdi
        leaq minima(%rip), %rsi
        leaq maxima(%rip), %rdx
.Lsensor_stat:
        movl 4(%rbx,%rcx,4), %eax
        addq %rax, (%rdi,%rcx,8)
        cmpl $1, valid_count(%rip)
        je .Linit_extrema
        cmpq (%rsi,%rcx,8), %rax
        jae .Lmaximum
        movq %rax, (%rsi,%rcx,8)
.Lmaximum:
        cmpq (%rdx,%rcx,8), %rax
        jbe .Lnext_sensor
        movq %rax, (%rdx,%rcx,8)
        jmp .Lnext_sensor
.Linit_extrema:
        movq %rax, (%rsi,%rcx,8)
        movq %rax, (%rdx,%rcx,8)
.Lnext_sensor:
        incl %ecx
        cmpl $4, %ecx
        jb .Lsensor_stat
        jmp .Lupdate_counts
.Lfault:
        incl fault_count(%rip)
.Lupdate_counts:
        # Effective flags/K are already zero for FAULT, so only fault advances.
        leaq current_counts(%rip), %rdi
        xorl %ecx, %ecx
.Lflag_count:
        movl %r14d, %eax
        movl %ecx, %edx
        addl $5, %ecx
        shrl %cl, %eax
        movl %edx, %ecx
        andl $1, %eax
        addl %eax, (%rdi,%rcx,4)
        incl %ecx
        cmpl $4, %ecx
        jb .Lflag_count
        movl %r14d, %eax
        shrl $9, %eax
        andl $7, %eax
        addl %eax, 16(%rdi)
        testl %eax, %eax
        setne %al
        movzbl %al, %eax
        addl %eax, 20(%rdi)
        movl %r14d, %eax
        shrl $15, %eax
        andl $1, %eax
        addl %eax, 24(%rdi)
        incl position(%rip)
        cmpl $VM_WINDOW_SAMPLES, position(%rip)
        jne .Lpack_row
        # Latch C+d, then clear C. This preserves the tenth sample.
        leaq current_counts(%rip), %rsi
        leaq completed_counts(%rip), %rdi
        movl $7, %ecx
        rep movsl
        leaq current_counts(%rip), %rdi
        movl $7, %ecx
        xorl %eax, %eax
        rep stosl
        movl $0, position(%rip)
        incl sequence(%rip)
.Lpack_row:
        leaq current_counts(%rip), %rdi
        call .Lpack_counts
        movl %eax, bus3(%rip)
        leaq completed_counts(%rip), %rdi
        call .Lpack_counts
        movl %eax, %r9d
        movl sequence(%rip), %r10d
        testl %r10d, %r10d
        setne %al
        movzbl %al, %eax
        shll $10, %eax
        shll $4, %r10d
        orl %eax, %r10d
        orl position(%rip), %r10d
        # Seventh printf argument is on the stack; reserve16 to retain alignment.
        subq $16, %rsp
        movq %r10, (%rsp)
        leaq row_format(%rip), %rdi
        movl %r12d, %esi
        movl %r15d, %edx
        movl %r14d, %ecx
        movl bus3(%rip), %r8d
        xorl %eax, %eax
        call printf@PLT
        addq $16, %rsp
        testl %eax, %eax
        js .Lio_error
        incl %r12d
        addq $24, %rbx
        jmp .Lrow
.Lstatistics:
        xorl %r12d, %r12d
.Lprint_sensor:
        leaq sensor_names(%rip), %rax
        movzbl (%rax,%r12), %esi
        cmpl $0, valid_count(%rip)
        je .Lprint_empty
        leaq sums(%rip), %rax
        movq (%rax,%r12,8), %r9
        movq %r9, %rax
        imulq $VM_AVERAGE_SCALE, %rax, %rax
        # Unsigned average_x100=floor(sum*100/count); valid_count is nonzero here.
        xorl %edx, %edx
        movl valid_count(%rip), %ecx
        divq %rcx
        movq %rax, %r15
        subq $16, %rsp
        movq %rax, (%rsp)
        leaq minima(%rip), %rax
        movq (%rax,%r12,8), %rcx
        leaq maxima(%rip), %rax
        movq (%rax,%r12,8), %r8
        movl valid_count(%rip), %edx
        leaq stat_format(%rip), %rdi
        xorl %eax, %eax
        call printf@PLT
        addq $16, %rsp
        testl %eax, %eax
        js .Lio_error
        movq %r15, %rax
        xorl %edx, %edx
        movl $100, %ecx
        divq %rcx
        movq %rdx, %rcx
        movq %rax, %rdx
        leaq sensor_names(%rip), %rax
        movzbl (%rax,%r12), %esi
        leaq average_format(%rip), %rdi
        xorl %eax, %eax
        call printf@PLT
        jmp .Lprinted_sensor
.Lprint_empty:
        leaq empty_format(%rip), %rdi
        xorl %eax, %eax
        call printf@PLT
.Lprinted_sensor:
        testl %eax, %eax
        js .Lio_error
        incl %r12d
        cmpl $4, %r12d
        jb .Lprint_sensor
        leaq summary_format(%rip), %rdi
        movl %r13d, %esi
        movl valid_count(%rip), %edx
        movl fault_count(%rip), %ecx
        movl last_warning(%rip), %r8d
        movl worst_warning(%rip), %r9d
        xorl %eax, %eax
        call printf@PLT
        testl %eax, %eax
        js .Lio_error
        leaq no_data_text(%rip), %rsi
        cmpl $-1, worst_warning(%rip)
        je .Lreport
        leaq normal_text(%rip), %rsi
        cmpl $0, worst_warning(%rip)
        je .Lreport
        leaq watch_text(%rip), %rsi
        cmpl $1, worst_warning(%rip)
        je .Lreport
        leaq danger_text(%rip), %rsi
.Lreport:
        leaq report_format(%rip), %rdi
        xorl %eax, %eax
        call printf@PLT
        testl %eax, %eax
        js .Lio_error
        leaq end_format(%rip), %rdi
        movl %r13d, %esi
        xorl %eax, %eax
        call printf@PLT
        testl %eax, %eax
        js .Lio_error
        xorl %edi, %edi
        call fflush@PLT
        testl %eax, %eax
        jne .Lio_error
        xorl %eax, %eax
        jmp .Lreturn
.Lshort_input:
        movq stdin(%rip), %rdi
        call ferror@PLT
        testl %eax, %eax
        jne .Lio_error
.Lbad_input:
        leaq input_error(%rip), %rdi
        movq stderr(%rip), %rsi
        call fputs@PLT
        movl $2, %eax
        jmp .Lreturn
.Lio_error:
        leaq output_error(%rip), %rdi
        movq stderr(%rip), %rsi
        call fputs@PLT
        movl $3, %eax
.Lreturn:
        addq $8, %rsp
        popq %r15
        popq %r14
        popq %r13
        popq %r12
        popq %rbx
        popq %rbp
        ret
.size main, .-main

# Leaf helper: RDI=row; returns EAX=B2, EDX=B1. Caller-saved registers only.
.Lclassify:
        xorl %r8d, %r8d
        xorl %r9d, %r9d
        xorl %r10d, %r10d
        xorl %esi, %esi
        leaq thresholds(%rip), %r11
.Lclass_sensor:
        movl 4(%rdi,%r8,4), %eax
        cmpl (%r11,%r8,4), %eax
        jbe .Lrange
        btsl %r8d, %r9d
.Lrange:
        cmpl $VM_INPUT_MAX, %eax
        jbe .Lpack_sensor
        btsl %r8d, %r10d
.Lpack_sensor:
        movl %r8d, %ecx
        shll $3, %ecx
        shll %cl, %eax
        orl %eax, %esi
        incl %r8d
        cmpl $4, %r8d
        jb .Lclass_sensor
        movl %r9d, %eax
        shll $16, %eax
        movl %r10d, %edx
        shll $20, %edx
        orl %edx, %eax
        orl 20(%rdi), %eax
        cmpl $15, 20(%rdi)
        jne .Lclass_fault
        testl %r10d, %r10d
        jne .Lclass_fault
        movl %r9d, %edx
        shll $5, %edx
        orl %edx, %eax
        orl $16, %eax
        xorl %r10d, %r10d
        xorl %ecx, %ecx
.Lpopcount:
        btl %ecx, %r9d
        adcl $0, %r10d
        incl %ecx
        cmpl $4, %ecx
        jb .Lpopcount
        movl %r10d, %edx
        shll $9, %edx
        orl %edx, %eax
        cmpl $2, %r10d
        jae .Lclass_danger
        testl %r10d, %r10d
        je .Lclass_return
        orl $0x1000, %eax
        jmp .Lclass_return
.Lclass_danger:
        orl $0x6000, %eax
        jmp .Lclass_return
.Lclass_fault:
        orl $0xb000, %eax
.Lclass_return:
        movl %esi, %edx
        ret

# Leaf helper: pack seven counters into B3/B4; returns EAX.
.Lpack_counts:
        xorl %eax, %eax
        xorl %r11d, %r11d
        leaq counter_shifts(%rip), %rsi
.Lpack_field:
        movl (%rdi,%r11,4), %edx
        movl (%rsi,%r11,4), %ecx
        shll %cl, %edx
        orl %edx, %eax
        incl %r11d
        cmpl $7, %r11d
        jb .Lpack_field
        ret

.section .note.GNU-stack,"",@progbits
