#include "PR/gbi.h"
#include "sys/print.h"

extern Gfx *gCurGfx;

void custom_game_tick(void) {
    diPrintf("hello precomp!");

    // // // // // // // // // // // // // 
    // Restore overwritten game_tick code
    diPrintfAll(&gCurGfx);
}
