#include <macro.inc>
.section .text

# void read_from_rom(u32 romAddr, u8* dst, s32 size)

# Patched in init_filesystem right after the call to osCreatePiManager
function custom_seg_load
    # Load custom segment
    la $a0, _customSegmentRomStart
    la $a1, _customSegmentStart
    lui $a2, %hi(_customSegmentSize)
    jal read_from_rom
     addiu $a2, $a2, %lo(_customSegmentSize)

    # Init custom segment
    # Init will also do the remainder of init_filesystem
    jal custom_init
     nop
    
    # Return from init_filesystem
    lw $ra, 0x14($sp)
    addiu $sp, $sp, 0x20
    jr $ra
     nop
