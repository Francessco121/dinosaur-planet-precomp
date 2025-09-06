# Assembly Macros (for DLL patches)

.set gp=64
.set noat
.set noreorder

.set K0BASE, 0x80000000
.set K1BASE, 0xA0000000
.set K2BASE, 0xC0000000

.macro .patch symbol offset=0x0
    .section .patch:\symbol:\offset,"x"
.endm
