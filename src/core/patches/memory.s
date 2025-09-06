#include <macro.inc>
.section .text

# To patch init_memory+0x14
function heap_start_patch
    lui $a3, %hi(_customSegmentNoloadEnd)
    addiu $a3, $a3, %lo(_customSegmentNoloadEnd)
