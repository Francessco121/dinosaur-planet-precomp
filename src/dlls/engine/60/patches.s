.include "dll_macro.inc"

# hook the dll_60_update1 export to allow the menu to be skipped
.patch .exports 0x10 # Export 0
    .dword splash_skip_helper

.text
function splash_skip_helper
    lui    $gp, %hi(_gp_disp)
    addiu  $gp, $gp, %lo(_gp_disp)
    addu   $gp, $gp, $t9
    addiu  $sp, $sp, -0x18
    sw     $ra, 0x10($sp)
    jal    splash_skip_update
     sw     $gp, 0x14($sp)
    lw     $gp, 0x14($sp)
    lw     $ra, 0x10($sp)
    j dll_60_update1
     addiu $sp, $sp, 0x18
.ifdef DEBUG
    jr $ra
     nop
.endif
endfunction splash_skip_helper
