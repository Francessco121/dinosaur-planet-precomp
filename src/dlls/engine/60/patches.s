.include "dll_macro.inc"

# Make the lightfoot background green!
.patch data_18
    .word 0x009c44ff

# dll_60_update2 does nothing, change it to run our custom code
.patch dll_60_update2
    b dll_60_custom_func
     nop
