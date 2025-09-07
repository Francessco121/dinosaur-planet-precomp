#if DEBUG

#include "sys/print.h"
#include "sys/gfx/texture.h"

extern char gDebugPrintBufferStart[0x900];
extern char *gDebugPrintBufferEnd;
extern s8 D_800931AC;
extern s8 D_800931B0;
extern s8 D_800931B4;
extern s8 D_800931B8;
extern Texture *gDiTextures[3];

void custom_diPrintfInit(void) {
    // @precomp: Remove code that scales up the rendered diPrintf text when
    // the resolution is above 320x240. This results in the text being way
    // too big for some reason.
    /*
    u32 fbRes;

    fbRes = get_some_resolution_encoded();
    if (RESOLUTION_WIDTH(fbRes) > 320) {
        D_800931AC = 1;
    }
    if (RESOLUTION_HEIGHT(fbRes) > 240) {
        D_800931B0 = 1;
    }
    */

    D_800931B4 = 0;
    D_800931B8 = 0;

    gDiTextures[0] = queue_load_texture_proxy(0);
    gDiTextures[1] = queue_load_texture_proxy(1);
    gDiTextures[2] = queue_load_texture_proxy(2);

    gDebugPrintBufferEnd = &gDebugPrintBufferStart[0];
}

int custom_diPrintf(const char* fmt, ...) {
    // @precomp: Restore diPrintf implementation
    va_list args;
    int written;

    va_start(args, fmt);

    if ((gDebugPrintBufferEnd - gDebugPrintBufferStart) > 0x800) {
        return -1;
    }

    sprintfSetSpacingCodes(TRUE);
    written = vsprintf(gDebugPrintBufferEnd, fmt, args);
    sprintfSetSpacingCodes(FALSE);

    if (written > 0) {
        gDebugPrintBufferEnd = &gDebugPrintBufferEnd[written] + 1;
    }

    va_end(args);

    return 0;
}

#else
typedef int prevent_pedantic_warning;
#endif // DEBUG
