OUTPUT_ARCH (mips)

#define BEGIN_SEG(name, addr) \
    _##name##SegmentStart = ADDR(.name); \
    _##name##SegmentRomStart = __romPos; \
    .name addr : AT(__romPos)

#define END_SEG(name) \
    _##name##SegmentEnd = ADDR(.name) + SIZEOF(.name); \
    _##name##SegmentRomEnd = __romPos + SIZEOF(.name); \
    _##name##SegmentSize = _##name##SegmentEnd - _##name##SegmentStart; \
    __romPos += SIZEOF(.name);

#define BEGIN_NOLOAD(name) \
    _##name##SegmentNoloadStart = ADDR(.name.noload); \
    .name.noload (NOLOAD) :

#define END_NOLOAD(name) \
    _##name##SegmentNoloadEnd = ADDR(.name.noload) + SIZEOF(.name.noload); \
    _##name##SegmentNoloadSize = _##name##SegmentNoloadEnd - _##name##SegmentNoloadStart;

#define PATCH(segment, symbol, offset) \
    .segment##symbol##offset##_patch symbol + offset : AT(_##segment##SegmentRomStart + symbol - _##segment##SegmentStart + offset)
    
#define CODE_PATCH(segment, symbol, offset) \
    .segment##symbol##offset##_patch symbol + offset : AT(segment##_ROM_START + symbol - segment##_VRAM + offset)

#define JAL_HOOK(segment, symbol, offset, helper, name) \
    .segment##symbol##offset##_patch symbol + offset : AT(segment##_ROM_START + symbol - segment##_VRAM + offset) \
    { \
        name = .; \
        BYTE(0x0C); \
        BYTE((helper >> 18) & 0xFF); \
        BYTE((helper >> 10) & 0xFF); \
        BYTE((helper >> 2)  & 0xFF); \
    }
#define J_HOOK_NOP(segment, symbol, offset, helper, name) \
    .segment##symbol##offset##_patch symbol + offset : AT(segment##_ROM_START + symbol - segment##_VRAM + offset) \
    { \
        name = .; \
        BYTE(0x08); \
        BYTE((helper >> 18) & 0xFF); \
        BYTE((helper >> 10) & 0xFF); \
        BYTE((helper >> 2)  & 0xFF); \
        BYTE(0x00); \
        BYTE(0x00); \
        BYTE(0x00); \
        BYTE(0x00); \
    }
    
#define ROM_PATCH(address) \
    .rom##address##_patch : AT(address)

SECTIONS
{
    __romPos = 0;

    BEGIN_SEG(baserom, 0)
    {
        BASEROM;
    }
    END_SEG(baserom)
    baseromEnd = __romPos;

    __romPos = 0xA4970;
    BEGIN_SEG(assets, .)
    {
        ASSETS;
    }
    END_SEG(assets)
    assetsEnd = __romPos;
    
    bss_end = 0xFFFFFFFF800D4370;
    . = bss_end;
    __romPos = ALIGN(__romPos, 16);
    BEGIN_SEG(custom, .)
    {
        BUILD_DIR/src/core/custom/init.o(.text);
        BUILD_DIR/src/core/custom/game_tick.o(.text);
        BUILD_DIR/src/core/custom/diprint.o(.text);
        BUILD_DIR/src/core/custom/vsprintf.o(.text);
        BUILD_DIR/src/core/custom/xldtob.o(.text);
        BUILD_DIR/src/core/custom/xprintf.o(.text);

        BUILD_DIR/src/core/custom/init.o(.*data*);
        BUILD_DIR/src/core/custom/game_tick.o(.*data*);
        BUILD_DIR/src/core/custom/diprint.o(.*data*);
        BUILD_DIR/src/core/custom/vsprintf.o(.*data*);
        BUILD_DIR/src/core/custom/xldtob.o(.*data*);
        BUILD_DIR/src/core/custom/xprintf.o(.*data*);

        . = ALIGN(16);
    }
    END_SEG(custom)
    BEGIN_NOLOAD(custom)
    {
        BUILD_DIR/src/core/custom/init.o(.bss);
        BUILD_DIR/src/core/custom/game_tick.o(.bss);
        BUILD_DIR/src/core/custom/diprint.o(.bss);
        BUILD_DIR/src/core/custom/vsprintf.o(.bss);
        BUILD_DIR/src/core/custom/xldtob.o(.bss);
        BUILD_DIR/src/core/custom/xprintf.o(.bss);

        . = ALIGN(16);
    }
    END_NOLOAD(custom)

    /* Patch init_memory to start heap after the custom segment (otherwise it overlaps). */
    CODE_PATCH(segment, init_memory, 0x14)
    {
        BUILD_DIR/src/core/patches/memory.o(.text);
    }

    /* Hijack init_filesystem right after osCreatePiManager is called to load our custom segment. */
    /* The custom init function will finish up what init_filesystem was originally doing. */
    CODE_PATCH(segment, init_filesystem, 0x54)
    {
        BUILD_DIR/src/core/patches/custom_seg_load.o(.text);
    }

    /* Patch out dongle check */
    CODE_PATCH(segment, check_dongle, 0x0)
    {
        BUILD_DIR/src/core/patches/dongle.o(.text);
    }

    /* Increase audio command list buffer size */
    /* The game overflows this in a few areas... */
    CODE_PATCH(segment, init_audio, 0x220)
    {
        BUILD_DIR/src/core/patches/audio_buffer.o(.text);
    }

    /* Hook game_tick right before diPrintfAll is called */
    JAL_HOOK(segment, game_tick, 0x230, custom_game_tick, custom_game_tick_hook)

    /* Restore diPrintf */
    J_HOOK_NOP(segment, diPrintfInit, 0x0, custom_diPrintfInit, custom_diPrintfInit_hook)
    J_HOOK_NOP(segment, diPrintf, 0x0, custom_diPrintf, custom_diPrintf_hook)

    /* Fix *printf floating point args */
    J_HOOK_NOP(segment, _Printf, 0x0, _Printf_patch, _Printf_patch_hook)
    J_HOOK_NOP(segment, _Ldtob, 0x0, _Ldtob_patched, _Ldtob_patched_hook)
    J_HOOK_NOP(segment, vsprintf, 0x0, custom_vsprintf, custom_vsprintf_hook)


    ROM_PATCH(0x000000)
    {
        BUILD_DIR/src/core/patches/header.o(.data);
    }

    /* Discard everything not specifically mentioned above. */
    /DISCARD/ :
    {
        *(*);
    }
}
