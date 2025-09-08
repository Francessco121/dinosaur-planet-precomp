#include "PR/gbi.h"
#include "sys/print.h"

extern Gfx *gCurGfx;
extern s32 dbg_heap_print(s32 arg0);

void custom_game_tick(void) {
#if DEBUG
    // Display memory heaps
    diPrintfSetBG(0, 0, 0, 255);
    dbg_heap_print(0);
#endif

    // // // // // // // // // // // // // 
    // Restore overwritten game_tick code
    diPrintfAll(&gCurGfx);
}
