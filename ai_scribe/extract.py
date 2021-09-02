from .syntax import SYNTAX

from . import scripting
from .scripting import translate, _CHARS

def get_subgraph(g, nodes=None):
    import functools
    nodes = nodes or functools.reduce(list.__add__, [list(g[cmd]) for cmd in SYNTAX])
    return g.subgraph(nodes)


def detect_bc(script_ptrs):
    """
    BC can use free space in places other than the contiguous block
    established in vanilla, we detect this to determine whether BC
    has already touched the scripts or not
    """
    oor_ptr = [ptr for ptr in script_ptrs
                           if ptr not in range(0xF8900, 0xFC24F)]
    return len(oor_ptr) == 0

def extract_scripts_bc():
    # FIXME: assumes bc libraries are imported
    from monsterrandomizer import get_monsters
    return {ent.name: ent.aiscript for ent in get_monsters()}
    # NOTE: for future reference
    # m.set_relative_ai(pointer)
    # m.aiscript = aiscript


def extract_scripts(romfile, script_ptrs, names):
    # scripts = dict(zip(script_ptrs, names[:-1]))
    script_ptrs = sorted(script_ptrs) + [0xFC050 - 0xF7000]

    scripts = dict(zip(script_ptrs, names))
    for sptr, eptr in zip(script_ptrs[:-1], script_ptrs[1:]):
        name = scripts.pop(sptr)
        scripts[name] = romfile[sptr:eptr]
        s = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        print(name, s.name + "\n", s.translate())
        # FIXME: don't override this
        s.name = name
        assert s.name == name, (s.name, name)
        assert s._bytes == scripts[name]
        scripts[name] = s

    return scripts

def extract(romfile=None, return_names=False):
    romfile = "Final Fantasy III (U) (V1.0) [!].smc"

    with open(romfile, "rb") as fin:
        romfile = fin.read()

    #SCRIPTS = romfile[SCRIPT_PTRS:0xF8900]
    SCRIPTS = romfile[0xF8400:0xF8700]
    script_ptrs = [int.from_bytes(bytes([low, high]), "little") + 0xF8700
                                for low, high in zip(SCRIPTS[::2], SCRIPTS[1::2])]

    name_idx = 0
    names = []
    #for sptr, eptr in zip(script_ptrs[:-1], script_ptrs[1:]):
    for _ in range(len(script_ptrs)):
        _name = romfile[0xFC050 + 10 * name_idx: 0xFC050 + 10 * (name_idx + 1)]
        name_idx += 1
        _name = name = "".join([_CHARS.get(i, "?") for i in _name])
        i = 1
        while True:
            if _name not in names:
                names.append(_name)
                break
            i += 1
            _name = name + str(i)

    names = dict(zip(names, script_ptrs))
    # Detect if BC has changed the scripts or their structure in some way
    is_bc = detect_bc(script_ptrs)
    if is_bc:
        scripts = extract_scripts_bc()
    else:
        scripts = extract_scripts(romfile, script_ptrs, names)

    with open("script_dump.txt", "w") as fout:
        for i, (name, script) in enumerate(scripts.items()):
            print(f"{i}: {name}\n\n{script.translate()}\n", file=fout)

    if return_names:
        return scripts, names
    return scripts

def _write_new(scripts, romfile):
    # DEPRECATED
    import command_graph
    cmd_graph = command_graph.CommandGraph()
    cmd_graph.from_scripts(scripts)

    NEW_SCRIPT = [240, 0x14, 0x14, 0x14, 253, 241, 54, 1, 255, 255]
    romout = romfile[:0xF8400] + bytearray([0] * 384 * 2) + romfile[:0xF8700]
    romout = romfile[:0xF8700] + bytearray(NEW_SCRIPT) + romfile[0xF8700 + len(NEW_SCRIPT):]

    # with open("test2.smc", "wb") as fout:
    #     fout.write(romout)

    WHELK_HEAD = 81
    WHELK_SHELL = 266

    WHELK_SCRIPT = list(scripts.values())[81]
    SHELL_SCRIPT = list(scripts.values())[266]

    NEW_WHELK_SCRIPT = cmd_graph.generate_from_graph()
    #NEW_WHELK_SCRIPT = [252, 1, 241, 54, 186, 5, 253, 255, 255]
    NEW_WHELK_SCRIPT = [240, 235, 254, 213, 255, 241, 75, 240, 114, 230, 230, 255]
    pad_bytes = len(WHELK_SCRIPT) - len(NEW_WHELK_SCRIPT)
    print(translate(NEW_WHELK_SCRIPT))
    NEW_WHELK_SCRIPT += [0xFF] * pad_bytes

    NEW_SHELL_SCRIPT = cmd_graph.generate_from_graph()
    #NEW_SHELL_SCRIPT = [240, 238, 238, 238, 253, 241, 54, 1, 255, 255]
    NEW_SHELL_SCRIPT = [244, 5, 0, 60, 248, 132, 132, 253, 241, 71, 244, 5, 0, 16, 253, 250, 9, 1, 54, 255, 252, 68, 253, 54, 247, 5, 255]
    pad_bytes = len(SHELL_SCRIPT) - len(NEW_SHELL_SCRIPT)
    print(translate(NEW_SHELL_SCRIPT))
    NEW_SHELL_SCRIPT += [0xFF] * pad_bytes

    romout = romfile[:]
    romout = romfile.replace(WHELK_SCRIPT, bytearray(NEW_WHELK_SCRIPT)) \
                    .replace(SHELL_SCRIPT, bytearray(NEW_SHELL_SCRIPT))

    # check byte difference

    with open("working/test.smc", "wb") as fout:
        fout.write(romout)

if __name__ == "__main__":
    extract()
