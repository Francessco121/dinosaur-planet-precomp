#include <macro.inc>
.section .text

function init_memory_patch
/* 17500 80016900 27BDFFD8 */  addiu      $sp, $sp, -0x28
/* 17504 80016904 3C058000 */  lui        $a1, %hi(osMemSize)
/* 17508 80016908 24A50318 */  addiu      $a1, $a1, %lo(osMemSize)
/* 1750C 8001690C AFBF0014 */  sw         $ra, 0x14($sp)
/* 17510 80016910 8CA30000 */  lw         $v1, 0x0($a1)
/* 17514 80016914 3C07800D */  #lui        $a3, %hi(bss_end)            # Start heaps after custom .bss end
/* 17518 80016918 24E74370 */  #addiu      $a3, $a3, %lo(bss_end)
                               lui        $a3, %hi(_customSegmentNoloadEnd)
                                addiu     $a3, $a3, %lo(_customSegmentNoloadEnd)
/* 1751C 8001691C 00E3082B */  sltu       $at, $a3, $v1
/* 17520 80016920 10200008 */  beqz       $at, .L80016944
/* 17524 80016924 00E01025 */   or        $v0, $a3, $zero
/* 17528 80016928 2404FFFF */  addiu      $a0, $zero, -0x1
/* 1752C 8001692C AC440000 */  sw         $a0, 0x0($v0)
.L80016930:
/* 17530 80016930 8CA30000 */  lw         $v1, 0x0($a1)
/* 17534 80016934 24420004 */  addiu      $v0, $v0, 0x4
/* 17538 80016938 0043082B */  sltu       $at, $v0, $v1
/* 1753C 8001693C 5420FFFC */  bnel       $at, $zero, .L80016930
/* 17540 80016940 AC440000 */   sw        $a0, 0x0($v0)
.L80016944:
/* 17544 80016944 3C01800B */  lui        $at, %hi(gHeapListSize)
/* 17548 80016948 A0200A70 */  sb         $zero, %lo(gHeapListSize)($at)
/* 1754C 8001694C 3C010080 */  lui        $at, (0x800000 >> 16)
/* 17550 80016950 10610009 */  beq        $v1, $at, .L80016978
/* 17554 80016954 3C048042 */  # lui       $a0, (0x8042C000 >> 16)      # Heap 0 addr: 0x8042C000 -> 0x8046C000
                                lui       $a0, 0x8046
    # No expansion
/* 17558 80016958 3C0E802D */  lui        $t6, (0x802D4000 >> 16)
/* 1755C 8001695C 35CE4000 */  ori        $t6, $t6, (0x802D4000 & 0xFFFF)
/* 17560 80016960 01C72823 */  subu       $a1, $t6, $a3
/* 17564 80016964 00E02025 */  or         $a0, $a3, $zero
/* 17568 80016968 0C005A78 */  jal        set_heap_block    # Heap 0 (no expansion)
/* 1756C 8001696C 240604B0 */   addiu     $a2, $zero, 0x4B0
/* 17570 80016970 10000013 */  b          .L800169C0
/* 17574 80016974 00000000 */   nop
    # Expansion
.L80016978:
/* 17578 80016978 3C05003D */  #lui        $a1, (0x3D4000 >> 16)
                               lui        $a1, 0x39                     # Heap 0 size: 0x3D4000 -> 0x394000 (3920k -> 3664k)
/* 1757C 8001697C 34A54000 */  ori        $a1, $a1, (0x3D4000 & 0xFFFF)
/* 17580 80016980 3484C000 */  ori        $a0, $a0, (0x8042C000 & 0xFFFF)
/* 17584 80016984 24060190 */  addiu      $a2, $zero, 0x190
/* 17588 80016988 0C005A78 */  jal        set_heap_block    # Heap 0
/* 1758C 8001698C AFA7001C */   sw        $a3, 0x1C($sp)
/* 17590 80016990 3C048024 */  lui        $a0, (0x80245000 >> 16)
/* 17594 80016994 3C05001E */  #lui        $a1, (0x1E7000 >> 16)
                               lui        $a1, 0x22                     # Heap 1 size: 0x1E7000 -> 0x227000 (1948k -> 2204k)
/* 17598 80016998 34A57000 */  ori        $a1, $a1, (0x1E7000 & 0xFFFF)
/* 1759C 8001699C 34845000 */  ori        $a0, $a0, (0x80245000 & 0xFFFF)
/* 175A0 800169A0 0C005A78 */  jal        set_heap_block    # Heap 1
/* 175A4 800169A4 24060320 */  # addiu     $a2, $zero, 0x320
                                addiu     $a2, $zero, 0x3E8             # Heap 1 slots: 0x320 -> 0x3E8 (800 -> 1000)
/* 175A8 800169A8 8FA4001C */  lw         $a0, 0x1C($sp)
/* 175AC 800169AC 3C0F8011 */  lui        $t7, (0x80119000 >> 16)
/* 175B0 800169B0 35EF9000 */  ori        $t7, $t7, (0x80119000 & 0xFFFF)
/* 175B4 800169B4 240604B0 */  #addiu      $a2, $zero, 0x4B0
                               addiu      $a2, $zero, 0x578             # Heap 2 slots: 0x4B0 -> 0x578 (1200 -> 1400)
/* 175B8 800169B8 0C005A78 */  jal        set_heap_block    # Heap 2
/* 175BC 800169BC 01E42823 */   subu      $a1, $t7, $a0
.L800169C0:
/* 175C0 800169C0 0C005C95 */  jal        func_80017254
/* 175C4 800169C4 24040002 */   addiu     $a0, $zero, 0x2
/* 175C8 800169C8 3C01800B */  lui        $at, %hi(pointerIntArrayCounter)
/* 175CC 800169CC A4201798 */  sh         $zero, %lo(pointerIntArrayCounter)($at)
/* 175D0 800169D0 8FBF0014 */  lw         $ra, 0x14($sp)
/* 175D4 800169D4 27BD0028 */  addiu      $sp, $sp, 0x28
/* 175D8 800169D8 03E00008 */  jr         $ra
/* 175DC 800169DC 00000000 */   nop
endfunction init_memory_patch
