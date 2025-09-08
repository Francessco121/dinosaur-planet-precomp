.include "dll_macro.inc"

# @dinomod:
# Initialize showInfoTextID to -1 instead of 0 to prevent the "info box" from rendering 
# in the uncleared framebuffer above the main viewport.
.patch dll_1_ctor 0x2C
    j ctor_patch__set_showInfoTextID
     nop
dll_1_ctor_patch_return:

.text
ctor_patch__set_showInfoTextID:
    # ctor code
    /* 0x2C */ addiu       $v0, $zero, -0x1
    /* 0x30 */ lw          $at, GOT_BSS($gp)
    # set showInfoTextID (.bss+0xC7C)
    sh $v0, 0xC7C($at)
    # return to ctor
    j dll_1_ctor_patch_return
     nop
.ifdef DEBUG
    jr $ra
     nop
.endif
