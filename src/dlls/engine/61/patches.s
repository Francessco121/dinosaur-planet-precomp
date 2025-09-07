.include "dll_macro.inc"

# hook dll_61_update1 to allow the menu to be skipped
.patch dll_61_update1
    b splash_skip_helper
     nop
    nop
dll_61_update1_patch_return:

.text
function splash_skip_helper
    lui    $gp, %hi(_gp_disp)
    addiu  $gp, $gp, %lo(_gp_disp)
    addu   $gp, $gp, $t9
    addiu  $sp, $sp, -0x2C
    sw     $ra, 0x10($sp)
    sw     $a0, 0x14($sp)
    sw     $a1, 0x18($sp)
    sw     $a2, 0x1C($sp)
    sw     $a3, 0x20($sp)
    sw     $gp, 0x24($sp)
    jal    splash_skip_update
     nop
    lw     $gp, 0x24($sp)
    lw     $ra, 0x10($sp)
    lw     $a0, 0x14($sp)
    lw     $a1, 0x18($sp)
    lw     $a2, 0x1C($sp)
    lw     $a3, 0x20($sp)
    j      dll_61_update1_patch_return
     addiu $sp, $sp, 0x2C
