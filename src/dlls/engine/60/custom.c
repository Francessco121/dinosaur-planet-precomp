#include "sys/controller.h"
#include "sys/main.h"
#include "sys/print.h"
#include "dll.h"

extern u8 data_0;
extern u8 data_4;

extern f32 bss_0;
extern s8 bss_4;
extern s8 bss_6;
extern f32 bss_8;
extern f32 bss_C;
extern f32 bss_10;

#if DEBUG
void dll_60_custom_func(void) {
    diPrintf("dll 60 bss_0 = %.2f\n", bss_0);
    diPrintf("dll 60 bss_6 = %d\n", bss_6);
}
#endif

void splash_skip_update(void) {
    if (data_4 == 1) {
        return;
    }

    if ((get_button_presses(0) & A_BUTTON) != 0) {
        // Fade in background if we haven't shown it yet
        if (bss_0 <= 240.0f) {
            gDLL_28_ScreenFade->vtbl->fade_reversed(30, SCREEN_FADE_BLACK);
        }
        // Let 1 frame render first so the background shows up for the next menu (we render it)
        bss_0 = 720.0f - delayFloat - 0.01f;
        bss_6 = 2;
    }
}
