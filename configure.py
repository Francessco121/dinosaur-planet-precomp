#!/usr/bin/env python3

import argparse
from enum import Enum
import glob
import os
from pathlib import Path
import sys
from typing import OrderedDict, TextIO
import ninja

from tools.fs_packer import FS_MAP

SCRIPT_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
DECOMP_DIR = Path("../dinosaur-planet").absolute().resolve()

class DecompFileCopy:
    def __init__(self, decomp_path: Path, build_path: Path):
        self.decomp_path = decomp_path
        self.build_path = build_path

class BuildFileType(Enum):
    C = 1
    ASM = 2

class BuildFile:
    def __init__(self, src_path: Path, obj_path: Path, type: BuildFileType):
        self.src_path = src_path
        self.obj_path = obj_path
        self.type = type

class DLL:
    def __init__(self, number: str, dir: Path, decomp_dir: Path, files: "list[BuildFile]"):
        self.number = number
        self.dir = dir
        self.decomp_dir = decomp_dir
        self.files = files

class BuildFiles:
    def __init__(self, 
                 core_files: "list[BuildFile]",
                 asset_copies: "list[DecompFileCopy]",
                 dll_copies: "list[DecompFileCopy]",
                 dlls: "list[DLL]"):
        self.core_files = core_files
        self.asset_copies = asset_copies
        self.dll_copies = dll_copies
        self.dlls = dlls

class BuildNinjaWriter:
    def __init__(self, writer: ninja.Writer, input: BuildFiles):
        self.writer = writer
        self.input = input
        self.link_deps: "list[str]" = []

    def write(self):
        # Write prelude (variables, rules)
        self.__write_prelude()

        # Write builds for core source compilation
        self.__write_core_file_builds()
        
        # Write DLL builds/linking/packing
        self.__write_dll_builds()

        # Write asset build/packing
        self.__write_asset_build()

        # Write main linker step
        self.__write_linking()

        # Write default target
        self.writer.default(["$BUILD_DIR/$TARGET.z64"])
    
    def __write_prelude(self):
        # Config
        self.writer.comment("Config (don't edit this directly!)")
        # TODO: make configurable
        self.writer.variable("TARGET", "dino")
        self.writer.variable("DECOMP_DIR", DECOMP_DIR.as_posix())
        
        self.writer.newline()

        # Write variables
        self.writer.comment("Variables")

        self.writer.variable("BUILD_DIR", "build")
        
        self.writer.variable("LD_SCRIPT", "$TARGET.ld")
        self.writer.variable("DLL_LD_SCRIPT", "dll.ld")

        self.writer.variable("ELF_IN", "$DECOMP_DIR/build/dino.elf")

        self.writer.variable("ELF", "$BUILD_DIR/$TARGET.elf")
        self.writer.variable("Z64", "$BUILD_DIR/$TARGET.z64")

        self.writer.variable("Z64_IN", "$BUILD_DIR/${TARGET}_in.bin")
        self.writer.variable("Z64_IN_OBJ", "$BUILD_DIR/${TARGET}_in.o")

        self.writer.variable("ASSETS_BIN", "$BUILD_DIR/${TARGET}_assets.bin")
        self.writer.variable("ASSETS_OBJ", "$BUILD_DIR/${TARGET}_assets.o")

        common_defines = [
            "-D_MIPS_SZLONG=32",
            "-DF3DEX_GBI_2",
        ]

        self.writer.variable("GCC_DEFINES", " ".join(common_defines))
        self.writer.variable("CC_DEFINES", " ".join(common_defines + ["-D_LANGUAGE_C"]))

        self.writer.variable("INCLUDES", " ".join([
            "-I include",
            "-I $DECOMP_DIR/include",
        ]))

        self.writer.variable("CFLAGS", " ".join([
            "-c",
            "-mabi=32",
            "-ffreestanding",
            "-mfix4300",
            "-G 0",
            "-fno-zero-initialized-in-bss",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
        ]))

        self.writer.variable("DLL_CFLAGS", " ".join([
            "-c",
            "-mips3",
            "-mabi=32",
            "-G 0",
            "-fPIC",
            "-mabicalls",
            "-fno-plt",
            "-mno-odd-spreg",
            "-nostdinc",
            "-ffreestanding",
            "-mfix4300",
            "-fno-zero-initialized-in-bss",
            "-mtune=vr4300",
            "-march=vr4300",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
        ]))

        self.writer.variable("ASFLAGS", " ".join([
            "-c",
            "-x assembler-with-cpp",
            "-mabi=32",
            "-ffreestanding",
            "-mfix4300",
            "-G 0",
            "-O",
        ]))

        self.writer.variable("DLL_ASFLAGS", " ".join([
            "-KPIC",
            "-mabi=32",
            "-modd-spreg",
            "-mips3",
            "-mtune=vr4300",
            "-march=vr4300",
            "-EB",
        ]))

        self.writer.variable("LDFLAGS", " ".join([
            "-T $BUILD_DIR/$LD_SCRIPT",
            "-mips3",
            "--accept-unknown-input-arch",
            "--no-check-sections",
        ]))

        self.writer.variable("DLL_LDFLAGS", " ".join([
            "-r",
            #"-m elf32btsmip",
            "-T $DLL_LD_SCRIPT",
            "-mips3",
            "--accept-unknown-input-arch",
            "--no-check-sections",
            "--no-gc-sections",
            "--discard-none",
            "--no-strip-discarded",
        ]))

        self.writer.variable("CPP_LDFLAGS", " ".join([
            "-P",
            "-Wno-trigraphs",
            "-DBUILD_DIR=$BUILD_DIR",
            "-Umips",
            "-DBASEROM=$Z64_IN_OBJ",
            "-DASSETS=$ASSETS_OBJ",
            "-I include",
        ]))

        self.writer.variable("OPTFLAGS", " ".join(["-Os"]))
        self.writer.variable("ELF_IN_TO_Z64_IN_FLAGS", " ".join([
            "-O binary",
            # We link in a repacked assets segment
            "--remove-section .assets",
            # Strip out data not used by the game to make room for new custom code
            "--remove-section .leftovers",
            "--remove-section .trailer",
        ]))
        self.writer.variable("BIN_TO_O_FLAGS", " ".join([
            "-I binary",
            "-O elf32-big",
        ]))

        self.writer.newline()

        cross = "mips64-ultra-elf-"

        self.writer.comment("Tools")
        self.writer.variable("GCC", f"{cross}gcc")
        self.writer.variable("AS", f"{cross}as")
        self.writer.variable("LD", f"{cross}ld")
        self.writer.variable("CPP", f"{cross}cpp")
        self.writer.variable("OBJCOPY", f"{cross}objcopy")
        self.writer.variable("CKSUM", f"{sys.executable} tools/n64cksum.py")
        self.writer.variable("FS_PACKER", f"{sys.executable} tools/fs_packer.py")
        self.writer.variable("ELF_PATCHER", f"{sys.executable} tools/elf_patcher.py")
        self.writer.variable("DINO_DLL", f"{sys.executable} $DECOMP_DIR/tools/dino_dll.py")
        self.writer.variable("ELF2DLL", f"{sys.executable} $DECOMP_DIR/tools/elf2dll.py")

        self.writer.newline()

        # Write rules
        self.writer.comment("Rules")
        self.writer.rule("gcc", 
            "$GCC $GCC_DEFINES $INCLUDES $CFLAGS $OPTFLAGS -MD -MF $out.d -o $out $in", 
            "Compiling $in...",
            depfile="$out.d")
        self.writer.rule("gcc_dll", 
            "$GCC $GCC_DEFINES $INCLUDES $DLL_CFLAGS $OPTFLAGS -MD -MF $out.d -o $out $in", 
            "Compiling $in...",
            depfile="$out.d")
        self.writer.rule("gcc_as", 
            "$GCC $ASFLAGS $INCLUDES -MD -MF $out.d -o $out $in", 
            "Compiling $in...",
            depfile="$out.d")
        self.writer.rule("as_dll", 
            "$AS $DLL_ASFLAGS $INCLUDES -MD $out.d -o $out $in", 
            "Compiling $in...",
            depfile="$out.d")
        self.writer.rule("ld", 
            "$LD -R $ELF_IN $LDFLAGS -Map $MAPFILE -o $out", 
            "Linking...")
        self.writer.rule("ld_dll", 
            "$LD $DLL_LDFLAGS -Map $MAPFILE -o $out $in", 
            "Linking...")
        self.writer.rule("cpp_ld", "$CPP $CPP_LDFLAGS -o $out $in", "Preprocessing $in...")
        self.writer.rule("to_bin", "$OBJCOPY $in $out -O binary", "Converting $in to $out...")
        # TODO: won't work on windows
        self.writer.rule("make_z64", "$OBJCOPY $in $out -O binary && $CKSUM $out", "Creating $out...")
        self.writer.rule("n64cksum", "$CKSUM $in", "Recomputing checksum...")
        self.writer.rule("elf_in_to_z64_in", "$OBJCOPY $in $out $ELF_IN_TO_Z64_IN_FLAGS", 
                         "Converting $in to $out...")
        self.writer.rule("bin_to_o", "$OBJCOPY $in $out $BIN_TO_O_FLAGS", 
                         "Converting $in to $out...")
        self.writer.rule("file_copy", "cp $in $out", "Copying $in to $out...")
        self.writer.rule("patch_elf", "$ELF_PATCHER -o $out $in", "Apply patches in $in...")
        self.writer.rule("elf2dll", "$ELF2DLL -o $out -b $DLL_BSS_TXT -s $DLL_SYMS_MAP $in", "Converting $in to DP DLL $out...")
        self.writer.rule("pack_fs", "$FS_PACKER -o $out $BUILD_DIR/assets", "Repacking assets...")
        self.writer.rule("pack_dlls", 
                         "$DINO_DLL pack $BUILD_DIR/assets/dlls $BUILD_DIR/assets/DLLS.bin $DECOMP_DIR/bin/assets/DLLS_tab.bin "
                            + "--tab_out $BUILD_DIR/assets/DLLS_tab.bin --quiet", 
                         "Repacking DLLs...")

        self.writer.newline()

    def __write_core_file_builds(self):
        self.writer.comment("Core source compilation")

        for file in self.input.core_files:
            # Determine command
            command: str
            if file.type == BuildFileType.C:
                command = "gcc"
            elif file.type == BuildFileType.ASM:
                command = "gcc_as"
            else:
                raise NotImplementedError()

            # Write command
            obj_build_path = f"$BUILD_DIR/{Path(file.obj_path).as_posix()}"
            src_build_path = Path(file.src_path).as_posix()
            self.writer.build(obj_build_path, command, src_build_path)
            self.link_deps.append(obj_build_path)

        self.writer.newline()

    def __write_dll_builds(self):
        pack_deps: "list[str]" = []

        self.writer.comment("DLL compilation")
        for dll in self.input.dlls:
            self.writer.comment(f"DLL {dll.number}")
            obj_dir = f"$BUILD_DIR/{dll.dir.as_posix()}"

            dll_link_deps: "list[str]" = []
            # The first link dep *MUST* be the ELF from the decomp
            dll_link_deps.append(f"$DECOMP_DIR/build/src/dlls/{dll.decomp_dir}/{dll.number}.elf")

            # Compile DLL sources
            for file in dll.files:
                # Determine command
                command: str
                if file.type == BuildFileType.C:
                    command = "gcc_dll"
                elif file.type == BuildFileType.ASM:
                    command = "as_dll"
                else:
                    raise NotImplementedError()
                
                # Write command
                obj_build_path = f"$BUILD_DIR/{Path(file.obj_path).as_posix()}"
                src_build_path = Path(file.src_path).as_posix()
                self.writer.build(obj_build_path, command, src_build_path)
                dll_link_deps.append(obj_build_path)
            
            # Link
            elf_path = f"{obj_dir}/{dll.number}.elf"
            mapfile_path = f"{obj_dir}/{dll.number}.map"

            self.writer.build(elf_path, "ld_dll", dll_link_deps,
                              variables={"MAPFILE": mapfile_path},
                              implicit_outputs=[mapfile_path])

            # Apply patches
            patched_elf_patch = f"{obj_dir}/{dll.number}.patched.elf"
            self.writer.build(patched_elf_patch, "patch_elf", elf_path)

            # Convert ELF to Dinosaur Planet DLL
            dll_asset_path = f"$BUILD_DIR/assets/dlls/{dll.number}.dll"
            dll_bss_asset_path = f"$BUILD_DIR/assets/dlls/{dll.number}.dll.bss.txt"
            dll_syms_map_asset_path = f"$BUILD_DIR/assets/dlls/{dll.number}.dll.syms.txt"
            self.writer.build(dll_asset_path, "elf2dll", patched_elf_patch,
                variables={
                    "DLL_BSS_TXT": dll_bss_asset_path,
                    "DLL_SYMS_MAP": dll_syms_map_asset_path
                },
                implicit_outputs=[dll_bss_asset_path, dll_syms_map_asset_path])
            pack_deps.append(dll_asset_path)
            pack_deps.append(dll_bss_asset_path)

        self.writer.newline()

        self.writer.comment("DLL copies (unmodified DLLs)")
        for copy in self.input.dll_copies:
            decomp_path = f"$DECOMP_DIR/{copy.decomp_path.as_posix()}"
            build_path = f"$BUILD_DIR/{copy.build_path.as_posix()}"
            self.writer.build(build_path, "file_copy", decomp_path)
            pack_deps.append(build_path)

        self.writer.newline()

        self.writer.comment("DLL packing")
        self.writer.build(
            ["$BUILD_DIR/assets/DLLS.bin", "$BUILD_DIR/assets/DLLS_tab.bin"], 
            "pack_dlls", implicit=pack_deps)

        self.writer.newline()

    def __write_asset_build(self):
        self.writer.comment("Asset packing")

        pack_deps: "list[str]" = [
            "$BUILD_DIR/assets/DLLS.bin", 
            "$BUILD_DIR/assets/DLLS_tab.bin"
        ]
        for copy in self.input.asset_copies:
            decomp_path = f"$DECOMP_DIR/{copy.decomp_path.as_posix()}"
            build_path = f"$BUILD_DIR/{copy.build_path.as_posix()}"
            self.writer.build(build_path, "file_copy", decomp_path)
            pack_deps.append(build_path)

        self.writer.build("$ASSETS_BIN", "pack_fs", implicit=pack_deps)

        self.writer.build("$ASSETS_OBJ", "bin_to_o", "$ASSETS_BIN")
        self.link_deps.append("$ASSETS_OBJ")

        self.writer.newline()

    
    def __write_linking(self):
        self.writer.comment("Linking")

        # Pre-process decomp elf
        self.writer.build("$Z64_IN", "elf_in_to_z64_in", "$ELF_IN")
        self.writer.build("$Z64_IN_OBJ", "bin_to_o", "$Z64_IN")
        self.link_deps.append("$Z64_IN_OBJ")

        # Pre-process linker script
        self.writer.build("$BUILD_DIR/$LD_SCRIPT", "cpp_ld", "$LD_SCRIPT")
        self.link_deps.append("$BUILD_DIR/$LD_SCRIPT")

        # Link
        self.writer.build("$BUILD_DIR/$TARGET.elf", "ld", [], 
                          implicit=self.link_deps,
                          variables={"MAPFILE": "$BUILD_DIR/$TARGET.map"}, 
                          implicit_outputs=["$BUILD_DIR/$TARGET.map"])

        # Convert .elf to .z64
        self.writer.build("$BUILD_DIR/$TARGET.z64", "make_z64", "$BUILD_DIR/$TARGET.elf")

class InputScanner:
    def __init__(self):
        pass

    def scan(self) -> BuildFiles:
        self.core_files: "list[BuildFile]" = []
        self.asset_copies: "list[DecompFileCopy]" = []
        self.dll_copies: "list[DecompFileCopy]" = []
        self.dlls: "list[DLL]" = []

        self.__scan_core_files()
        self.__scan_dlls()
        self.__scan_assets()

        return BuildFiles(self.core_files, self.asset_copies, self.dll_copies, self.dlls)

    def __scan_core_files(self):
        c_paths = [Path(path) for path in glob.glob("src/core/**/*.c", recursive=True)]
        for src_path in c_paths:
            obj_path = self.__make_obj_path(src_path)
            self.core_files.append(BuildFile(src_path, obj_path, BuildFileType.C))
        
        s_paths = [Path(path) for path in glob.glob("src/core/**/*.s", recursive=True)]
        for src_path in s_paths:
            obj_path = self.__make_obj_path(src_path)
            self.core_files.append(BuildFile(src_path, obj_path, BuildFileType.ASM))
    
    def __scan_dlls(self):
        src_dlls_path = Path("src/dlls")

        # TODO: support for custom *new* DLLs (this would need to just skip the decomp dlls.txt lookup) 

        # Parse the decomp's dlls.txt
        decomp_dlls_txt_path = DECOMP_DIR.joinpath("src/dlls/dlls.txt")
        assert decomp_dlls_txt_path.exists(), f"Missing dlls.txt file at {decomp_dlls_txt_path.absolute()}"
        
        with open(decomp_dlls_txt_path, "r", encoding="utf-8") as decomp_dlls_txt_file:
            decomp_dlls_txt = self.__parse_dlls_txt(decomp_dlls_txt_file)

        # Parse our dlls.txt
        dlls_txt_path = src_dlls_path.joinpath("dlls.txt")
        assert dlls_txt_path.exists(), f"Missing dlls.txt file at {dlls_txt_path.absolute()}"
        
        with open(dlls_txt_path, "r", encoding="utf-8") as dlls_txt_file:
            dlls_txt = self.__parse_dlls_txt(dlls_txt_file)

        dll_dirs = [(n, src_dlls_path.joinpath(path)) for (n, path) in dlls_txt.items()]

        # Find DLL patches/custom code
        to_compile: "set[int]" = set()
        for (number, dir) in dll_dirs:
            decomp_dir = decomp_dlls_txt[number]
            assert decomp_dir != None

            c_paths = [Path(path) for path in glob.glob(f"{dir}/**/*.c", recursive=True)]
            asm_paths = [Path(path) for path in glob.glob(f"{dir}/**/*.s", recursive=True)]

            files: "list[BuildFile]" = []

            for src_path in c_paths:
                obj_path = self.__make_obj_path(src_path)
                files.append(BuildFile(src_path, obj_path, BuildFileType.C))
            
            for src_path in asm_paths:
                obj_path = self.__make_obj_path(src_path)
                files.append(BuildFile(src_path, obj_path, BuildFileType.ASM))
            
            self.dlls.append(DLL(str(number), dir, decomp_dir, files))
            to_compile.add(number)

        # Copy over remaining unmodified DLLs
        for i in range(796):
            if (i + 1) in to_compile:
                continue

            self.dll_copies.append(DecompFileCopy(
                Path(f"bin/assets/dlls/{i + 1}.dll"), Path(f"assets/dlls/{i + 1}.dll")))

    def __scan_assets(self):
        SKIP_ASSETS = set([
            # Rebuild ourselves
            "DLLS.bin", # 46
            "DLLS_tab.bin", # 47
            #"DLLSIMPORTTAB.bin", # 48 # TODO
            # Zero size assets don't exist
            "CACHEFON.bin", # 11
            "CACHEFON2.bin", # 12
            "VOXOBJ.bin", # 3A
        ])

        for asset in FS_MAP:
            if asset in SKIP_ASSETS:
                continue
            self.asset_copies.append(DecompFileCopy(
                Path(f"bin/assets/{asset}"), Path(f"assets/{asset}")))
    
    def __make_obj_path(self, path: Path) -> Path:
        return path.with_suffix('.o')
    
    def __parse_dlls_txt(self, file: TextIO) -> "OrderedDict[int, str]":
        path_map: "OrderedDict[int, str]" = {}

        for line in file.readlines():
            stripped = line.lstrip()
            if len(stripped) == 0 or stripped.isspace() or stripped.startswith("#"):
                continue

            pair = stripped.split("=")
            if len(pair) == 2:
                number = int(pair[0].rstrip())
                path = pair[1].strip()
                path_map[number] = path
        
        return path_map

def main():
    parser = argparse.ArgumentParser(description="Creates the Ninja build script for Dinosaur Planet precomp.")
    parser.add_argument("--base-dir", type=str, dest="base_dir", help="The root of the project.", default=str(SCRIPT_DIR))
    
    args = parser.parse_args()

    # Do all path lookups from the base directory
    os.chdir(Path(args.base_dir).resolve())

    # Gather input files
    scanner = InputScanner()
    input = scanner.scan()

    # Write ninja build file
    with open("build.ninja", "w") as ninja_file:
        writer = BuildNinjaWriter(ninja.Writer(ninja_file), input)
        writer.write()


if __name__ == "__main__":
    main()
