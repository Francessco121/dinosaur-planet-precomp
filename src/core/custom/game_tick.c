#include "PR/gbi.h"
#include "sys/print.h"

extern Gfx *gCurGfx;

void custom_game_tick(void) {
#if DEBUG
    diPrintf("hello precomp!");
#endif
    // // // // // // // // // // // // // 
    // Restore overwritten game_tick code
    diPrintfAll(&gCurGfx);
}
