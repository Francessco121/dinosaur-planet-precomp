# Handles precomp .patch* sections for ELF files

import argparse
import math
import re
from typing import Protocol
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection, Relocation
from elftools.elf.sections import Section, SymbolTableSection, Symbol
from io import BufferedReader, BufferedWriter, BytesIO
import os

class PatcherException(Exception):
    pass

class EditedSection(Protocol):
    def __init__(self, section: Section):
        self.section = section
    
    def write(self, writer: BufferedWriter):
        raise NotImplementedError()

class EditedRawSection(EditedSection):
    def __init__(self, section):
        super().__init__(section)
        self.data = BytesIO(section.data())
    
    def write(self, writer: BufferedWriter):
        self.data.seek(0, os.SEEK_SET)
        writer.write(self.data.read())
        self.section.header['sh_size'] = self.data.tell()

class EditedRelocationSection(EditedSection):
    def __init__(self, section):
        assert isinstance(section, RelocationSection)
        super().__init__(section)
        self.relocations = [r for r in section.iter_relocations()]
    
    def write(self, writer: BufferedWriter):
        start = writer.tell()
        for reloc in self.relocations:
            reloc.entry["r_info"] = ((reloc.entry["r_info_sym"] & 0xFFFFFF) << 8) | (reloc.entry["r_info_type"] & 0xFF)
            self.section.entry_struct.build_stream(reloc.entry, writer)
        self.section.header['sh_size'] = writer.tell() - start

class EditedSymbolTableSection(EditedSection):
    def __init__(self, section):
        assert isinstance(section, SymbolTableSection)
        super().__init__(section)
        self.syms = [s for s in section.iter_symbols()]
        self.original_sym_indexes: dict[Symbol, int] = {}
        self.syms_by_name: dict[str, Symbol] = {}
        for i, sym in enumerate(self.syms):
            self.original_sym_indexes[sym] = i
            existing_by_name = self.syms_by_name.get(sym.name)
            # If there are duplicate symbols, take the first defined version if possible
            if existing_by_name == None or existing_by_name.entry['st_shndx'] == 'SHN_UNDEF':
                self.syms_by_name[sym.name] = sym

    def write(self, writer: BufferedWriter):
        start = writer.tell()
        for sym in self.syms:
            self.section.elffile.structs.Elf_Sym.build_stream(sym.entry, writer)
        self.section.header['sh_size'] = writer.tell() - start

class EditedELF:
    def __init__(self, elf: ELFFile, sections: list[EditedSection]):
        self.elf = elf
        self.sections = sections
        self.original_section_indexes: dict[EditedSection, int] = {}
        self.sections_by_name: dict[str, EditedSection] = {}
        self.symtab = None
        for i, section in enumerate(sections):
            self.original_section_indexes[section] = i
            self.sections_by_name[section.section.name] = section

            if isinstance(section, EditedSymbolTableSection):
                assert self.symtab == None
                self.symtab = section
        assert self.symtab != None

def align(n: int, alignment: int) -> int:
    return math.ceil(n / alignment) * alignment

# .patch:<symbol>:<offset>
PATCH_SECTION_NAME_REGEX = re.compile(r"\.patch:(\w+):(\w+)")
VALID_PATCH_SECTION_TARGETS = set([".text", ".rodata", ".data"])

def do_patching(elf: EditedELF):
    shstrtab: EditedRawSection = elf.sections[elf.elf.header['e_shstrndx']]
    patch_sections: list[EditedSection] = []

    for idx, section in enumerate(elf.sections):
        section_name = section.section.name
        match = PATCH_SECTION_NAME_REGEX.match(section_name)
        if match != None:
            assert isinstance(section, EditedRawSection)
            patch_sections.append(section)

            # Lookup symbol that the patch is relative to
            symbol_name = match.group(1)

            sym = elf.symtab.syms_by_name.get(symbol_name)
            if sym == None:
                raise PatcherException(f"Patch section '{section_name}' references unknown symbol: '{symbol_name}'")

            # Lookup section the symbol is in
            sym_shndx = sym.entry["st_shndx"]
            if sym_shndx == "SHN_UNDEF":
                raise PatcherException(f"Patch section '{section_name}' references symbol '{symbol_name}' which does not have a section defined.")
            if sym_shndx == "SHN_ABS":
                raise PatcherException(
                    f"Patch section '{section_name}' references an absolute symbol '{symbol_name}', which is not supported. " +
                    "Please use a symbol with a defined section or make the patch relative to a section instead.")
            if sym_shndx < 0 or sym_shndx >= len(elf.sections):
                raise PatcherException(f"Patch section '{section_name}' references symbol '{symbol_name}' which has an invalid section index.")
            sym_section = elf.sections[sym_shndx]
            assert isinstance(sym_section, EditedRawSection)
            patch_section_name: str = sym_section.section.name
            if not patch_section_name in VALID_PATCH_SECTION_TARGETS:
                raise PatcherException(
                    f"Patch section '{section_name}' references symbol '{symbol_name}' which is in an invalid section: '{patch_section_name}'")
            patch_section_name = patch_section_name.lstrip(".")

            # Calculate section relative offset
            offset = int(match.group(2), base=0)
            offset += sym.entry["st_value"]

            # Patch in code/data
            sym_section.data.seek(offset, os.SEEK_SET)
            sym_section.data.write(section.data.read())
            size = section.data.tell()

            # Migrate relocations to target section
            reloc_section = elf.sections_by_name.get(f".rel{section_name}")
            if reloc_section != None:
                assert isinstance(reloc_section, EditedRelocationSection)
                patch_sections.append(reloc_section)
                
                target_reloc_section_name = f".rel{sym_section.section.name}"
                target_reloc_section = elf.sections_by_name.get(target_reloc_section_name)
                if target_reloc_section == None:
                    # Target relocation section doesn't exist, so make it
                    target_reloc_section = EditedRelocationSection(
                        RelocationSection(
                            reloc_section.section.header.copy(),
                            target_reloc_section_name,
                            reloc_section.section.elffile))
                    shstrtab.data.seek(0, os.SEEK_END)
                    sh_name = shstrtab.data.tell()
                    shstrtab.data.write(target_reloc_section_name.encode())
                    header = target_reloc_section.section.header
                    header["sh_name"] = sh_name
                    header["sh_info"] = sym_shndx
                    elf.sections.append(target_reloc_section)
                    elf.sections_by_name[target_reloc_section_name] = target_reloc_section
                    elf.original_section_indexes[target_reloc_section] = len(elf.sections) - 1

                # Remove relocations overwritten by patch
                relocs_to_remove: list[Relocation] = []
                for reloc in target_reloc_section.relocations:
                    base_offset = reloc["r_offset"]
                    if base_offset >= offset and base_offset < (offset + size):
                        relocs_to_remove.append(reloc)
                for reloc in relocs_to_remove:
                    target_reloc_section.relocations.remove(reloc)

                for reloc in reloc_section.relocations:
                    # Relocate reloc to patched location relative to the section being patched
                    reloc.entry["r_offset"] += offset
                    target_reloc_section.relocations.append(reloc)
            
            # Migrate symbols to target section
            for sym in elf.symtab.syms:
                if sym.entry["st_shndx"] == idx and sym.entry["st_info"]["type"] != "STT_SECTION":
                    sym.entry["st_value"] += offset
                    sym.entry["st_shndx"] = sym_shndx
            
    # Remove patch sections (clean up)
    for section in patch_sections:
        elf.sections.remove(section)
    
    section_symbols: list[Symbol] = []
    for sym in elf.symtab.syms:
        if sym.entry["st_info"]["type"] == "STT_SECTION" and PATCH_SECTION_NAME_REGEX.match(sym.name) != None:
            section_symbols.append(sym)
    for sym in section_symbols:
        elf.symtab.syms.remove(sym)

def remap(elf: EditedELF):
    # Re-sort symbols (local symbols must always be first)
    elf.symtab.syms.sort(key=lambda s: 0 if s.entry["st_info"]["bind"] == "STB_LOCAL" else 1)

    last_local_sym = 0
    for i, sym in enumerate(elf.symtab.syms):
        if sym.entry["st_info"]["bind"] == "STB_LOCAL":
            last_local_sym = i

    # sh_info of .symtab is one plus the index of the last local symbol
    elf.symtab.section.header["sh_info"] = last_local_sym + 1

    # Re-map section references
    section_remap: dict[int, int] = {}
    for i, section in enumerate(elf.sections):
        section_remap[elf.original_section_indexes[section]] = i
    
    for section in elf.sections:
        if not section.section.is_null():
            sheader = section.section.header
            sheader['sh_link'] = section_remap.get(sheader['sh_link'], 0)
            if isinstance(section, EditedRelocationSection):
                sheader['sh_info'] = section_remap.get(sheader['sh_info'], 0)
        if isinstance(section, EditedSymbolTableSection):
            for sym in section.syms:
                sym_shndx = sym.entry["st_shndx"]
                if isinstance(sym_shndx, int):
                    sym.entry["st_shndx"] = section_remap.get(sym_shndx, "SHN_UNDEF")
    
    elf.elf.header['e_shstrndx'] = section_remap.get(elf.elf.header['e_shstrndx'], 0)
    
    # Re-map symbol references
    sym_remap: dict[int, int] = {}
    for i, sym in enumerate(elf.symtab.syms):
        sym_remap[elf.symtab.original_sym_indexes[sym]] = i

    for section in elf.sections:
        if isinstance(section, EditedRelocationSection):
            for reloc in section.relocations:
                reloc_symidx = reloc.entry['r_info_sym']
                reloc.entry['r_info_sym'] = sym_remap.get(reloc_symidx, "STN_UNDEF")

def patch_file(elf_file: BufferedReader, output: BufferedWriter):
    # Read base ELF
    elf = ELFFile(elf_file)

    sections: list[EditedSection] = []
    for section in elf.iter_sections():
        if isinstance(section, RelocationSection):
            sections.append(EditedRelocationSection(section))
        elif isinstance(section, SymbolTableSection):
            sections.append(EditedSymbolTableSection(section))
        else:
            sections.append(EditedRawSection(section))

    # Patch
    edited_elf: EditedELF = EditedELF(elf, sections)
    do_patching(edited_elf)
    remap(edited_elf)

    # Write patched ELF
    sections_by_file_order: list[EditedSection] = edited_elf.sections.copy()
    sections_by_file_order.sort(key=lambda s: s.section.header['sh_offset'])
    
    output.write(bytearray(elf.structs.Elf_Ehdr.sizeof()))

    for section in sections_by_file_order:
        if section.section.is_null():
            continue
        section.section.header['sh_offset'] = output.tell()
        if section.section.header['sh_type'] != "SHT_NOBITS":
            section.write(output)

            pad_to = align(output.tell(), 4)
            output.write(bytearray(max(pad_to - output.tell(), 0)))
    
    elf.header['e_shoff'] = output.tell()
    elf.header['e_shnum'] = len(edited_elf.sections)
    for section in edited_elf.sections:
        elf.structs.Elf_Shdr.build_stream(section.section.header, output)

    output.seek(0, os.SEEK_SET)
    elf.structs.Elf_Ehdr.build_stream(elf.header, output)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=argparse.FileType("rb"), help="The ELF file containing patch sections.")
    parser.add_argument("-o", "--output", type=argparse.FileType("wb"), help="The path of the patched ELF file to output.", required=True)
    args = parser.parse_args()

    error = False
    try:
        patch_file(args.elf, args.output)
    except PatcherException as ex:
        print(f"ERROR: {ex}")
        error = True
    finally:
        args.elf.close()
        args.output.close()
    
    if error:
        exit(1)

if __name__ == "__main__":
    main()