from .scripting import Script
def package_rom(romfile, outf="test.smc"):
    pass

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