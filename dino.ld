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
    _##name##SegmentNoloadEnd = ADDR(.name.noload) + SIZEOF(.name.noload);

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
    
    bss_end = 0xFFFFFFFF800D4370;
    . = bss_end;
    BEGIN_SEG(custom, .)
    {
        BUILD_DIR/src/custom/init.o(.text);
        BUILD_DIR/src/custom/game_tick.o(.text);
        BUILD_DIR/src/custom/diprint.o(.text);

        BUILD_DIR/src/custom/init.o(.*data*);
        BUILD_DIR/src/custom/game_tick.o(.*data*);
        BUILD_DIR/src/custom/diprint.o(.*data*);
    }
    END_SEG(custom)
    BEGIN_NOLOAD(custom)
    {
        BUILD_DIR/src/custom/init.o(.bss);
        BUILD_DIR/src/custom/game_tick.o(.bss);
        BUILD_DIR/src/custom/diprint.o(.bss);
    }
    END_NOLOAD(custom)

    /* Patch init_memory to start heap after the custom segment (otherwise it overlaps). */
    CODE_PATCH(segment, init_memory, 0x14)
    {
        BUILD_DIR/src/patches/memory.o(.text);
    }

    /* Hijack init_filesystem right after osCreatePiManager is called to load our custom segment. */
    /* The custom init function will finish up what init_filesystem was originally doing. */
    CODE_PATCH(segment, init_filesystem, 0x54)
    {
        BUILD_DIR/src/patches/custom_seg_load.o(.text);
    }

    /* Patch out dongle check */
    CODE_PATCH(segment, check_dongle, 0x0)
    {
        BUILD_DIR/src/patches/dongle.o(.text);
    }

    /* Patch out more security checks */
    /* TODO: do these properly with actual DLL patches */
    /* 0x38317CC + 0xAB70 + 0x6500 */
    ROM_PATCH(0x384283C)
    {
        /* b L_8101254C */
        BYTE(0x10);
        BYTE(0x00);
        BYTE(0x00);
        BYTE(0x12);
    }
    /* 0x38317CC + 0xE7CA0 + 0xA7D4 */
    ROM_PATCH(0x3923C40)
    {
        /* b L_81177828 */
        BYTE(0x10);
        BYTE(0x00);
        BYTE(0x00);
        BYTE(0x14);
    }

    /* Hook game_tick right before diPrintfAll is called */
    JAL_HOOK(segment, game_tick, 0x230, custom_game_tick, custom_game_tick_hook)

    /* Restore diPrintf */
    J_HOOK_NOP(segment, diPrintfInit, 0x0, custom_diPrintfInit, custom_diPrintfInit_hook)
    J_HOOK_NOP(segment, diPrintf, 0x0, custom_diPrintf, custom_diPrintf_hook)

    ROM_PATCH(0x000000)
    {
        BUILD_DIR/src/patches/header.o(.data);
    }

    /* Discard everything not specifically mentioned above. */
    /DISCARD/ :
    {
        *(*);
    }
}
