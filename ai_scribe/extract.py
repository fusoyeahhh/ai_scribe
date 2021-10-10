import logging
log = logging.getLogger("ai_scribe")
log.setLevel(logging.INFO)

from .syntax import SYNTAX

from . import _NAME_ALIASES
from . import scripting
from .scripting import translate, _CHARS

# Allow no more than this number of 0xFF bytes in a potential script
_MAX_FF_TOLERANCE = 16

# BC specific changes
# Coloseum Chupon gets a fuller script (no longer Sneezes) [Nothing to change there]
# Shiva / Ifrit become two random Espers [index 264, 265] -- realias
# Umaro / Umaro2 become named after in game char [index 271, 272]
# Tritoch / Tritoch2 becomes a random Esper [index 276, 277, 324] --- realias
# TODO: check on Final Kefka manager [index 282]
# Colossus is co-opted to a new entity [index 310]
# K@N got weird [index 330]
# Final Kefka got weird [index 310]
# Magimaster is renamed [index 358]

# FIXME: Helper class while we transition indexing schemes
class ScriptSet:
    def _get_index(self, name):
        # case 1 --- in dedup aliases
        if name in self.aliased_names:
            return self.aliased_names.index(name)

        # case 2 --- in aliases
        if name in _NAME_ALIASES:
            return _NAME_ALIASES[name]

        # case 3 --- integer index, not in aliases
        if isinstance(name, int):
            # Has to be an index
            return name

        # case 4 string, not aliased, must be canonical name
        return self.canonical_names.index(name)

    def __init__(self, romfile):
        self.scripts = None
        self.canonical_names = None
        self.init_from_rom(romfile)

    def init_from_rom(self, romfile):
        self.scripts, self.canonical_names = extract(romfile, return_names=True)
        self.aliased_names = extract_names(romfile, alias_duplicates=True)

    def __getitem__(self, name):
        return self.scripts[self._get_index(name)]

    def get_ordered_script_array(self):
        return [self.scripts[n] for n in range(len(self.scripts))]

def get_subgraph(g, nodes=None):
    import functools
    nodes = nodes or functools.reduce(list.__add__, [list(g[cmd]) for cmd in SYNTAX])
    return g.subgraph(nodes)

def non_vanilla_ptrs(script_ptrs):
    return [ptr for ptr in script_ptrs if ptr not in range(0xF8700, 0xFC050)]

def detect_bc(script_ptrs):
    """
    BC can use free space in places other than the contiguous block
    established in vanilla, we detect this to determine whether BC
    has already touched the scripts or not
    """
    return len(non_vanilla_ptrs(script_ptrs)) > 0

_FIX_MAG_ROADER = True
def _check_and_fix_script_exceptions(name, script):
    if name in {"Mag Roader4", 243} and _FIX_MAG_ROADER:
        script._bytes += b'\xFF'
        log.info("Mag Roader4 is known to have a script bug: it has no ending byte. Fix requested and applied")
        scripting.Script.validate(script._bytes)
    else:
        raise ValueError(f"Got invalid script [{name}] with no known fix.")

    return script

EVENT_TO_CANONICAL_NAME_MAP = {
    0x4: "Tritoch",
    0x5: "Whelk",
    0x6: "M-TekArmor",
    0x7: "Vargas",
    0x8: "Vargas",
    0x9: "Vargas",
    0xA: "Ultros",
    0xD: "Gau",
    0xE: "Officer",
    0xF: "Merchant",
    0x10: "TunnelArmr",
    0x11: "",
    0x12: "Tritoch2",
    0x13: "10",
    0x14: "10",
    0x15: "10",
    0x16: "Ultros3",
    0x17: "5",
    0x18: "10",
    0x1A: "9",
    0x1C: "Gau",
    0x1D: "2",
    0x1E: "10",
    0x1F: "Wrexsoul",
    0x20: "Kefka2",
}
def identify_special_event_scripts(scripts):
    rename = {}
    for name, script in scripts.items():
        # In vanilla (and probably BC) 0xF7 can't appear in an
        # enemy script unless it refers to an argument or variable of
        # some kind (e.g. *not* the desperation attack byte)
        if 0xF7 in script._bytes:
            idx = script._bytes.index(0xF7)
            rename[name] = script._bytes[idx + 1]

    return rename

def identify_zone_eater(scripts, rename=False):
    for name, script in scripts.items():
        if 0xD5 in script._bytes:
            if rename:
                scripts["Zone Eater"] = scripts.pop(name)
            return name
    return None

def extract_scripts(romfile, script_ptrs, names, unused_bytes=7):
    # FIXME: index this properly
    scripts = dict(zip(script_ptrs, names))
    scripts = dict(sorted(scripts.items(), key=lambda t: t[0]))
    _ptrs = scripts.copy()

    non_std_ptrs = non_vanilla_ptrs(script_ptrs)
    non_std_ptrs = {ptr: name for ptr, name in scripts.items()
                                            if ptr in non_std_ptrs}

    # We don't know if these bytes are used or not
    # FIXME: just clip the last script
    if len(non_std_ptrs) > 0:
        unused_bytes = 0
        scripts = {ptr: name for ptr, name in scripts.items()
                                           if ptr not in non_std_ptrs}

    # clip unused bytes at the end of the block
    script_ptrs = [*scripts] + [0xFC050 - unused_bytes]

    invalid = {}
    #scripts = {v: k for k, v in scripts.items()}
    for i, (sptr, eptr) in enumerate(zip(script_ptrs[:-1], script_ptrs[1:])):
        name = scripts.pop(sptr)
        bin_script = romfile[sptr:eptr]
        try:
            scripting.Script.validate(bin_script, allow_empty_fc=True)
        except Exception as e:
            #raise ValueError(f"Script for {name} is invalid.")
            invalid[name] = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        s = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        log.debug(f"{name} {s.name}\n{s.translate()}")
        # FIXME: obviated
        assert s.name == name, (s.name, name)
        assert s._bytes == bin_script

        scripts[name] = s

    # Handle scripts in nonstandard locations
    for ptr, name in non_std_ptrs.items():
        log.info(f"Non standard pointer location {hex(ptr)} -> {name}")
        # heuristic: count number of end blocks
        # This will be confused by the appearance of "Nothing" in skill selection lists
        # So, we try to acquire blocks until it "makes sense"...
        eptr, _script = ptr, b''
        while _script.count(b'\xFF') <= _MAX_FF_TOLERANCE:
            eptr = romfile.index(b'\xFF', eptr) + 1
            _script = romfile[ptr:eptr]

            # Try to validate
            try:
                scripting.Script.validate(_script, allow_empty_fc=True)
            except Exception as e:
                log.debug(e)
                continue

            # If validation succeeds, and we have two valid blocks
            # we have a valid script
            script = scripting.Script(_script, name)
            try:
                # FIXME: can't check for nff >= 2, condition can be triggered
                # by incomplete scripts
                if script.translate().count("END BLOCK") == 2:
                    break
            except Exception as e:
                log.debug(e)
                continue

        # This is only executed if we hit the maximum tolerance,
        # which is a failure condition
        else:
            log.error(f"Script for {name} cannot be properly parsed; "
                      "it is likely that this is an invalid script. "
                      "If possible, script follows:")
            log.error(script.translate(allow_partial=True, memblk=True))
            exit()

        if eptr - ptr >= 1000:
            log.warning(f"Script for {name} is very long ({eptr - ptr} bytes); "
                        "it is likely that this is an invalid script.")

        scripts[name] = script

    # Handle scripts with known bugs / odd features
    for name, script in invalid.items():
        try:
            invalid[name] = _check_and_fix_script_exceptions(name, script)
        except Exception as e:
            # Vanilla and no recourse, so we abort
            if len(non_std_ptrs) == 0:
                raise e
            log.warning(f"Script for [{name}] seems to be invalid, but with no specified fix. "
                        "Because BC has already modified the scripts, we assume this is non-fatal "
                        "and will take no further action. This may cause future problems.")

    return scripts

def extract_battle_msgs(romfile):
    battle_msg_ptrs  = romfile[0xFDFE0:0xFE1E0]
    battle_msg_ptrs = [int.from_bytes(bytes([low, high]), "little") + 0xF0000
                        for low, high in zip(battle_msg_ptrs[::2], battle_msg_ptrs[1::2])]

    # bookend the ptrs on the end
    battle_msg_ptrs.append(0xFF44F)
    battle_msg_ptrs = sorted([t[::-1] for t in enumerate(battle_msg_ptrs)], key=lambda t: t[0])
    battle_msgs = {}
    for ptr1, ptr2 in zip(battle_msg_ptrs[:-1], battle_msg_ptrs[1:]):
            ptr1, i = ptr1
            ptr2 = ptr2[0]
            battle_msgs[i] = romfile[ptr1:ptr2]

            # TODO: translate

    return battle_msgs

def extract_names(romfile, alias_duplicates=True, offset=0xFC050, name_len=10, total_names=384):
    if isinstance(romfile, str):
        with open(romfile, "rb") as fin:
            romfile = fin.read()

    names = []
    ptrs = [offset + name_len * idx for idx in range(total_names + 1)]
    for idx, (s, e) in enumerate(zip(ptrs[:-1], ptrs[1:])):
        _name = name = "".join([_CHARS.get(i, "?") for i in romfile[s:e]])

        i = 1
        while alias_duplicates:
            if _name not in names:
                names.append(_name)
                break
            i += 1
            _name = name + str(i)
        else:
            names.append(_name)

    return names

def extract_script_ptrs(romfile, block_offset=0xF8700, offset=0xF8400, total_ptrs=384):
    if isinstance(romfile, str):
        with open(romfile, "rb") as fin:
            romfile = fin.read()

    chunk = romfile[offset:offset + total_ptrs * 2]
    script_ptrs = [int.from_bytes(bytes([low, high]), "little") + block_offset
                   for low, high in zip(chunk[::2], chunk[1::2])]

    return script_ptrs

def extract(romfile=None, return_names=False, force_bc=False):
    #romfile = "Final Fantasy III (U) (V1.0) [!].smc"
    #romfile = "base_roms/Final_Fantasy_3_Textless.1620609722.smc"

    with open(romfile, "rb") as fin:
        romfile = fin.read()

    script_ptrs = extract_script_ptrs(romfile)
    # Canonical names
    names = extract_names(romfile, alias_duplicates=False)
    _names = [*range(len(names))]

    # Detect if BC has changed the scripts or their structure in some way
    is_bc = force_bc or detect_bc(script_ptrs)
    log.info(f"ROM type: {'bc' if is_bc else 'vanilla'}")

    if force_bc:
        scripts = extract_scripts(romfile, script_ptrs, _names, unused_bytes=0)
    else:
        scripts = extract_scripts(romfile, script_ptrs, _names)

    # map script to canonical name
    #scripts = {n: scripts[idx] for idx, n in enumerate(_names)}

    # can't alias names if they've been changed
    # Moreover, since the renaming is order dependent ('kefka2' -> ...)
    # we can't even aliases bosses consistently
    # This block attempts to fix this by searching for special events or skills
    # and renaming them back to the vanilla equivalents
    # FIXME: this will cause some crucial event scripts to be clipped if we go over
    # TODO: ensure all event scripts are written to beginning of block
    #if is_bc:
    if False:
        # identify a few key enemies and name them back to their vanilla equivalents
        _name = identify_zone_eater(scripts)
        name = "Zone Eater"
        if name in names:
            log.debug(f"Identified {name} as {_name}, swapping to avoid confusion.")
            # FIXME: you can't swap these, I think
            # FIXME: the name order can't change, since insertion order in the dict maps
            # to the index of the name in the rom
            # Maybe make a copy of the script with a "*" prepended as a reminder to
            # handle it specially
            names[_name], names[name] = names[name], names[_name]
            scripts[_name], scripts[name] = scripts[name], scripts[_name]
        else:
            log.debug(f"Identified Zone Eater as {_name}, renaming back to avoid confusion.")
            names["Zone Eater"] = names.pop(_name)
            scripts[_name] = scripts.pop(name)

        # Rename L255. back
        if "L.255Magic" in names:
            log.debug(f"Identified MagiMaster as L255.Magic, renaming back to avoid confusion.")
            names["MagiMaster"] = names.pop("L.255Magic")
            scripts["MagiMaster"] = scripts.pop("L.255Magic")

        # Find all special event scripts and ensure they are also vanilla
        # This eases the location of potentially relocated / unnamed scripts
        # and their protection against being randomized
        for name, value in identify_special_event_scripts(scripts).items():
            _name = EVENT_TO_CANONICAL_NAME_MAP[value]
            if _name in names:
                log.debug(f"Identified {name} as {_name}, swapping to avoid confusion.")
                names[_name], names[name] = names[name], names[_name]
                scripts[_name], scripts[name] = scripts[name], scripts[_name]
            else:
                log.debug(f"Identified {name} as {_name}, renaming back to avoid confusion.")
                names[_name] = names.pop(name)
                scripts[_name] = scripts.pop(name)

        # Detect Espers
        from .flags import ESPERS
        espers = (set(names) & set(ESPERS.values())) - {"Tritoch"}
        assert len(espers) == 2
        rename = dict(zip(("Ifrit", "Shiva"), espers))
        for n, e in rename.items():
            scripts[n] = scripts.pop(e)
            names[n] = names.pop(e)
            log.debug(f"Identified {n} as {e}, renaming back to avoid confusion.")

    if return_names:
        return scripts, names
    return scripts

# Unused, could be in the future if fully integrated with BC
def extract_scripts_bc():
    try:
        from monsterrandomizer import get_monsters
    except ImportError as e:
        print(e)
        exit("BC libraries are required to access scripts in a pre-randomized ROM.")
    return {ent.name: ent.aiscript for ent in get_monsters()}
    # NOTE: for future reference
    # m.set_relative_ai(pointer)
    # m.aiscript = aiscript

if __name__ == "__main__":
    extract()
