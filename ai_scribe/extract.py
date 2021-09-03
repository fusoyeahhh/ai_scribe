import logging
log = logging.getLogger("ai_scribe")
log.setLevel(logging.INFO)

from .syntax import SYNTAX

from . import _NAME_ALIASES
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
    try:
        from monsterrandomizer import get_monsters
    except ImportError as e:
        print(e)
        exit("BC libraries are required to access scripts in a pre-randomized ROM.")
    return {ent.name: ent.aiscript for ent in get_monsters()}
    # NOTE: for future reference
    # m.set_relative_ai(pointer)
    # m.aiscript = aiscript


def extract_scripts(romfile, script_ptrs, names):
    # scripts = dict(zip(script_ptrs, names[:-1]))

    scripts = dict(zip(script_ptrs, names))
    scripts = dict(sorted(scripts.items(), key=lambda t: t[0]))
    script_ptrs = [*scripts] + [0xFC050 - 0xF7000]

    #scripts = {v: k for k, v in scripts.items()}
    for sptr, eptr in zip(script_ptrs[:-1], script_ptrs[1:]):
        name = scripts.pop(sptr)
        scripts[name] = romfile[sptr:eptr]
        s = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        log.debug(name, s.name + "\n", s.translate())
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

    # Alias blank names to something more useful
    names = [_NAME_ALIASES.get(n, n) for n in names]

    names = dict(zip(names, script_ptrs))
    # Detect if BC has changed the scripts or their structure in some way
    is_bc = detect_bc(script_ptrs)
    log.info(f"ROM type: {'bc' if is_bc else 'vanilla'}")
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

if __name__ == "__main__":
    extract()
