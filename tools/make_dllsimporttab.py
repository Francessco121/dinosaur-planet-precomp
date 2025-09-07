import argparse
import struct
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from io import BufferedReader, BufferedWriter
import re
from typing import TextIO

symbol_pattern = re.compile(r"(\S+)\s*=\s*(\S+);")

class ScriptException(Exception):
    pass

def make(base: BufferedReader, elf_file: BufferedReader, syms_file: TextIO, output: BufferedWriter, linker_script: TextIO):
    syms = [s.strip() for s in syms_file.readlines() if len(s.strip()) > 0 and not s.lstrip().startswith("#")]

    elf = ELFFile(elf_file)
    symtab = elf.get_section_by_name(".symtab")
    assert isinstance(symtab, SymbolTableSection)

    output.write(base.read())

    i = 0x80000000 + (base.tell() // 4) + 1
    for sym_name in syms:
        sym = symtab.get_symbol_by_name(sym_name)
        if sym == None:
            raise ScriptException(f"Unknown symbol to export: '{sym_name}'")
        if len(sym) > 1:
            raise ScriptException(f"Export symbol '{sym_name}' is ambiguous.")
        sym = sym[0]
        if sym.entry["st_shndx"] == "SHN_UNDEF":
            raise ScriptException(f"Export symbol '{sym_name}' is undefined.")

        output.write(struct.pack(">I", sym.entry["st_value"]))
        linker_script.write("{} = 0x{:X};\n".format(sym_name, i))
        i += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dllsimporttab", type=argparse.FileType("rb"), help="Path to the original DLLSIMPORTTAB file.")
    parser.add_argument("-e", "--elf", type=argparse.FileType("rb"), help="Path to the base ELF file.", required=True)
    parser.add_argument("-s", "--symbols", type=argparse.FileType("r"), help="Path to a file containing new symbols to export to DLLs.", required=True)
    parser.add_argument("-o", "--output", type=argparse.FileType("wb"), help="The path of the new DLLSIMPORTTAB file to output.", required=True)
    parser.add_argument("-l", "--linker-script", dest="linker_script", type=argparse.FileType("w"), help="The path of the linker script containing the new symbols to output.", required=True)
    args = parser.parse_args()

    error = False
    try:
        make(args.dllsimporttab, args.elf, args.symbols, args.output, args.linker_script)
    except ScriptException as ex:
        print(f"ERROR: {ex}")
        error = True
    finally:
        args.dllsimporttab.close()
        args.elf.close()
        args.symbols.close()
        args.output.close()
        args.linker_script.close()
    
    if error:
        exit(1)

if __name__ == "__main__":
    main()