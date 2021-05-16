import networkx.algorithms

import scripting
from extract import *

def package_rom(romfile, outf="test.smc"):
    pass

def _validate(script):
    if not script[-1] == 0xFF:
        return False

    # This checks for exactly two 0xFF and that the script isn't empty
    # NOTE: This will be confused by 0xFF ("nothing") in skill based commands
    try:
        ffi2 = script.index(0xFF, script.index(0xFF) + 1)
    except ValueError:
        return False

    # This checks that the script isn't "empty"
    if ffi2 <= 1:
        return False

    return True

# Script replacement
def replace_script(g, ptr, **kwargs):
    pass

SCRIPT_BLOCK_LEN = 0xFC050 - 0xF8900
def randomize_scripts(g, n=384, ptr_off=0, **kwargs):
    scripts = []
    _n = n
    while len(scripts) < _n:
        scripts += filter(_validate, [g.generate_from_graph(**kwargs) for _ in range(_n - len(scripts))])
        scripts = scripts[:n]

    # Pair down longest scripts until we arrive at something we can fit in the ROM space
    while sum(map(len, scripts)) > SCRIPT_BLOCK_LEN:
        scripts = sorted(scripts, key=len)
        scripts[-1] = g.generate_from_graph(**kwargs)

    # FIXME: separate to pack function
    ptrs = [ptr_off] + [*map(len, scripts)][:-1]
    s = ptr_off
    for _ in range(len(ptrs)):
        s += ptrs.pop(0)
        ptrs.append(s)
    return scripts, ptrs