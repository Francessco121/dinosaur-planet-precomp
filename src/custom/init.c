#include "PR/os.h"
#include "sys/fs.h"
#include "sys/memory.h"

extern u8 _customSegmentNoloadStart[];
extern u8 _customSegmentNoloadEnd[];

extern Fs * gFST;
extern u32 gLastFSTIndex;
extern s32 __fstAddress;
extern s32 __file1Address;

extern void read_from_rom(u32 romAddr, u8* dst, s32 size);

void custom_init(void) {
    // Finish loading filesystem (custom_seg_load replaced this)
    s32 size;

    // A4AA0 - A4970
    size = (s32)&__file1Address - (s32)&__fstAddress;

    gFST = (Fs *)malloc(size, 0x7F7F7FFF, NULL);
    read_from_rom((u32)&__fstAddress, (u8 *)gFST, size);

    // Finish loading custom code segment
    bzero(_customSegmentNoloadStart, _customSegmentNoloadEnd - _customSegmentNoloadStart);
}
