#include <macro.inc>
.section .text

function audio_buffer_size_patch
    li $t9, 0x5000 # Original was 0x4000
