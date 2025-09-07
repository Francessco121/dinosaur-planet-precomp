#if DEBUG

#include "PR/os.h"
#include "PR/ultratypes.h"
#include "libc/stdarg.h"
#include "libc/xstdio.h"

static void *proutSprintf(void *dst, const char *buf, size_t size) {
    bcopy(buf, dst, size);
	return (void*)((char*)dst + size);
}

// @precomp: Redirect vsprintf to our patched _Printf to get float printing to work
int custom_vsprintf(char *s, const char *fmt, va_list args) {
    int ret = _Printf(&proutSprintf, (void*)s, fmt, args);
	if (0 <= ret) {
		s[ret] = '\0';
    }
	
    return (ret);
}

#else
typedef int prevent_pedantic_warning;
#endif // DEBUG
