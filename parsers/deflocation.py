#!/usr/bin/env python
import sys
import os

sys.path[0:0] = [".", ".."]

import pyelftools
from pyelftools.elftools.elf.elffile import ELFFile
from pyelftools.elftools.dwarf.descriptions import (
    describe_DWARF_expr, set_global_machine_arch)
from pyelftools.elftools.dwarf.locationlists import (
    LocationEntry, LocationExpr, LocationParser)


def patch_locations() :
    pass

if __name__ == "__main__" :
    pass
