# Dinosaur Planet Precomp Example

An example of using precomp with Dinosaur Planet.

For details on what precomp is, see https://github.com/Mr-Wiseguy/N64-Precomp-Example.

## Prerequisites

- The [Dinosaur Planet Decompilation project](https://github.com/zestydevy/dinosaur-planet)
    - Note: This project currently assumes that the decomp is found at `../dinosaur-planet` relative to this directory. 
- MIPS64 `binutils` and `gcc` via [N64 Development tools (glankk/n64)](https://github.com/glankk/n64)
    - Tooling currently expects these to be available with the `mips64-ultra-elf-` prefix.
- [Ninja](https://ninja-build.org/)

## Building

0. (optional) Set up a Python virtual environment and run `pip install -r requirements.txt`
1. Run a build for the Dinosaur Planet decompilation.
2. Run `./configure.py`
3. Run `ninja`
