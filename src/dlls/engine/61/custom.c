#include "sys/controller.h"
#include "sys/main.h"
#include "sys/menu.h"
#include "dll.h"

extern s8 bss_2;

void splash_skip_update(void) {
    if ((get_button_presses(0) & A_BUTTON) != 0) {
        bss_2 = 1;
    }
}
