import logging
log = logging.getLogger("ai_scribe")

from .scripting import Script
def package_rom(romfile, outf="test.smc"):
    pass

# Make a dict of the name -> script length
# then write scripts in the order you want
# construct pointers as the previous step happens
# replace script length with cumulative offset
def pack_scripts(export, names, write_first=set(), offset=0):
    # FIXME: do Dummies last
    # Make the first script a do nothing and point to zero
    # instead on any irregularity

    # TODO: assert s.name == n
    _ptrs, last = {}, offset
    ptrs, scr = [], []
    for n in write_first:
        _ptrs[n] = last
        scr.append(export[n]._bytes)
        log.debug(f"{n}: {hex(names[n])} -> {hex(0xF8700 + last)}")
        last += len(export[n])

    # TODO: remap pointers in actual dictionary
    for n in names:
        if n in write_first:
            ptrs.append(_ptrs[n])
        else:
            ptrs.append(last)
            scr.append(export[n]._bytes)
            log.debug(f"{n}: {hex(names[n])} -> {hex(0xF8700 + last)}")
            last += len(export[n])

    return scr, ptrs


SCRIPT_BLOCK_LEN = 0xFC050 - 0xF8700
def randomize_scripts(g, n=384, ptr_off=0, total_len=SCRIPT_BLOCK_LEN, **kwargs):
    scripts = []
    _n = n
    while len(scripts) < _n:
        scripts += [g.generate_from_graph(**kwargs) for _ in range(_n - len(scripts))]
        scripts = [script for script in scripts if Script.validate(bytes(script))][:n]

    # Pair down longest scripts until we arrive at something we can fit in the ROM space
    while sum(map(len, scripts)) > total_len:
        scripts = sorted(scripts, key=len)
        try:
            scripts[-1] = g.generate_from_graph(**kwargs)
        except SyntaxError as e:
            print(e)
            raise ValueError("Encountered problem generating script with args: " +
                              str(kwargs))

    # FIXME: separate to pack function
    ptrs = [ptr_off] + [*map(len, scripts)][:-1]
    s = ptr_off
    for _ in range(len(ptrs)):
        s += ptrs.pop(0)
        ptrs.append(s)
    return scripts, ptrs