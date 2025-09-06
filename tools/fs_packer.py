import argparse
from io import BufferedReader
import math
import os
from pathlib import Path
import struct

FS_MAP = [
    "AUDIO_tab.bin", # 00
    "AUDIO.bin", # 01
    "SFX_tab.bin", # 02
    "SFX.bin", # 03
    "AMBIENT_tab.bin", # 04
    "AMBIENT.bin", # 05
    "MUSIC_tab.bin", # 06
    "MUSIC.bin", # 07
    "MPEG_tab.bin", # 08
    "MPEG.bin", # 09
    "MUSICACTIONS.bin", # 0A
    "CAMACTIONS.bin", # 0B
    "LACTIONS.bin", # 0C
    "ANIMCURVES.bin", # 0D
    "ANIMCURVES_tab.bin", # 0E
    "OBJSEQ2CURVE_tab.bin", # 0F
    "FONTS.bin", # 10
    "CACHEFON.bin", # 11
    "CACHEFON2.bin", # 12
    "GAMETEXT.bin", # 13
    "GAMETEXT_tab.bin", # 14
    "GLOBALMAP.bin", # 15
    "TABLES.bin", # 16
    "TABLES_tab.bin", # 17
    "SCREENS.bin", # 18
    "SCREENS_tab.bin", # 19
    "VOXMAP.bin", # 1A
    "VOXMAP_tab.bin", # 1B
    "TEXPRE_tab.bin", # 1C
    "TEXPRE.bin", # 1D
    "WARPTAB.bin", # 1E
    "MAPS.bin", # 1F
    "MAPS_tab.bin", # 20
    "MAPINFO.bin", # 21
    "MAPSETUP.bin", # 22
    "MAPSETUP_tab.bin", # 23
    "TEX1.bin", # 24
    "TEX1_tab.bin", # 25
    "TEXTABLE.bin", # 26
    "TEX0.bin", # 27
    "TEX0_tab.bin", # 28
    "BLOCKS.bin", # 29
    "BLOCKS_tab.bin", # 2A
    "TRKBLK.bin", # 2B
    "HITS.bin", # 2C
    "HITS_tab.bin", # 2D
    "MODELS_tab.bin", # 2E
    "MODELS.bin", # 2F
    "MODELIND.bin", # 30
    "MODANIM_tab.bin", # 31
    "MODANIM.bin", # 32
    "ANIM_tab.bin", # 33
    "ANIM.bin", # 34
    "AMAP_tab.bin", # 35
    "AMAP.bin", # 36
    "BITTABLE.bin", # 37
    "WEAPONDATA.bin", # 38
    "VOXOBJ_tab.bin", # 39
    "VOXOBJ.bin", # 3A
    "MODLINES.bin", # 3B
    "MODLINES_tab.bin", # 3C
    "SAVEGAME.bin", # 3D
    "SAVEGAME_tab.bin", # 3E
    "OBJSEQ.bin", # 3F
    "OBJSEQ_tab.bin", # 40
    "OBJECTS_tab.bin", # 41
    "OBJECTS.bin", # 42
    "OBJINDEX.bin", # 43
    "OBJEVENT.bin", # 44
    "OBJHITS.bin", # 45
    "DLLS.bin", # 46
    "DLLS_tab.bin", # 47
    "DLLSIMPORTTAB.bin", # 48
    "ENVFXACT.bin", # 49
]

def align(n: int, alignment: int) -> int:
    return math.ceil(n / alignment) * alignment

def repack(assets_path: Path, output_writer: BufferedReader):
    file_count = len(FS_MAP)

    output_writer.write(bytearray(align((file_count + 2) * 4, 16)))

    fst_byte_size = output_writer.tell()
    assert(fst_byte_size == (0xA4AA0 - 0xA4970))

    offset = 0
    fst: list[int] = []
    fst.append(file_count)

    for filename in FS_MAP:
        fst.append(offset)
        filepath = assets_path.joinpath(filename)
        if filepath.exists():
            with open(filepath, "rb") as file:
                output_writer.write(file.read())
                offset += file.tell()
        #else:
        #    print(f"not found {filepath.absolute()}")

    fst.append(offset)

    # HACK: the decomp extract is missing the last 4 bytes of ENVFXACT...
    #       it's just zeroes
    fst[len(fst) - 1] += 4
    output_writer.write(bytearray(4))

    output_writer.seek(0, os.SEEK_SET)
    for offset in fst:
        output_writer.write(struct.pack(">I", offset))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", type=str, help="The directory of assets to repack.")
    parser.add_argument("-o", "--output", type=argparse.FileType("wb"), help="The path of the assets binary file to output.", required=True)
    args = parser.parse_args()

    repack(Path(args.assets), args.output)
    
    args.output.close()

if __name__ == "__main__":
    main()