import logging
log = logging.getLogger("ai_scribe")
log.setLevel(logging.INFO)

from .syntax import SYNTAX

from . import _NAME_ALIASES
from . import scripting
from .scripting import translate, _CHARS

# Allow no more than this number of 0xFF bytes in a potential script
_MAX_FF_TOLERANCE = 16

# FIXME: Helper class while we transition indexing schemes
class ScriptSet:
    def _get_index(self, name):
        # BC specific changes
        if self.is_bc:
            # Coloseum Chupon gets a fuller script (no longer Sneezes) [Nothing to change there]
            # Final Kefka is something else now
            if name == "Kefka":
                return 298
            # Kefka at Narshe
            if name == "Kefka3":
                return 330
            # Shiva / Ifrit become two random Espers [index 264, 265] -- realias
            if name == "Shiva":
                return 264
            if name == "Ifrit":
                return 265
            # Umaro / Umaro2 become named after in game char [index 271, 272]
            if name == "Umaro":
                return 271
            if name == "Umaro2":
                return 272
            # Tritoch / Tritoch2 becomes a random Esper [index 276, 277, 324] --- realias
            if name == "Tritoch":
                return 276
            if name == "Tritoch2":
                return 277
            if name == "Tritoch3":
                return 324
            # Colossus is co-opted to a new entity [index 310]
            if name == "Colossus":
                return 310
            # Magimaster is renamed [index 358]
            if name == "MagiMaster":
                return 358
            # Final Kefka is in a different place (282)
            if name == "Kefka2":
                return 282
            if name == "5":
                return 282
            if name == "False Kefka":
                # Maybe??
                return 298
            # TODO: tier manager seems to have disappeared?

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
        self.script_ptrs = None
        self.canonical_names = None
        self.is_bc = False
        self.init_from_rom(romfile)

    def init_from_rom(self, romfile):
        self.scripts, self.canonical_names, self.script_blocks = extract(romfile, return_names=True)
        self.script_ptrs = extract_script_ptrs(romfile)
        self.is_bc = detect_bc(self.script_ptrs)
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
    return [ptr for ptr in script_ptrs
                    if ptr not in range(0xF8700, 0xFC050)]

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
        details = script.translate(allow_partial=True, memblk=True)
        raise ValueError(f"Got invalid script {str(script)} with no known fix. Script details follow:\n{details}")

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
    events = {}
    for name, script in scripts.items():
        # In vanilla (and probably BC) 0xF7 can't appear in an
        # enemy script unless it refers to an argument or variable of
        # some kind (e.g. *not* the desperation attack byte)
        # FIXME: make has_xxx_byte and has_special_event, etc...
        if 0xF7 in script._bytes:
            idx = script._bytes.index(0xF7)
            events[script._bytes[idx + 1]] = name

    return events

def identify_formation_alterations(scripts):
    alts = {}
    for name, script in scripts.items():
        # In vanilla (and probably BC) 0xF5 can't appear in an
        # enemy script unless it refers to an argument or variable of
        # some kind (e.g. *not* the desperation attack byte)
        # FIXME: make has_xxx_byte and has_special_event, etc...
        if 0xF5 in script._bytes:
            idx = script._bytes.index(0xF5)
            alts[name] = tuple(script._bytes[idx + 1:idx + 4])

    return alts

def identify_formation_swaps(scripts):
    swaps = {}
    for name, script in scripts.items():
        # In vanilla (and probably BC) 0xF2 can't appear in an
        # enemy script unless it refers to an argument or variable of
        # some kind (e.g. *not* the desperation attack byte)
        # FIXME: make has_xxx_byte and has_special_event, etc...
        if 0xF2 in script._bytes:
            idx = script._bytes.index(0xF2)
            swaps[name] = tuple(script._bytes[idx + 1:idx + 4])

    return swaps

def identify_special_animations(scripts):
    anim = {}
    for name, script in scripts.items():
        # In vanilla (and probably BC) 0xFA can't appear in an
        # enemy script unless it refers to an argument or variable of
        # some kind (e.g. *not* the desperation attack byte)
        # FIXME: make has_xxx_byte and has_special_event, etc...
        if 0xFA in script._bytes:
            idx = script._bytes.index(0xFA)
            anim[name] = tuple(script._bytes[idx + 1:idx + 4])

    return anim

def extract_scripts(romfile, script_ptrs, names, return_blocks=False):
    # FIXME: script_ptrs should index like an array to avoid duplicate names
    scripts = dict(zip(names, script_ptrs))
    scripts = dict(sorted(scripts.items(), key=lambda t: t[1]))
    _ptrs = scripts.copy()

    non_std_ptrs = non_vanilla_ptrs(script_ptrs)
    non_std_ptrs = {name: ptr for name, ptr in scripts.items()
                                            if ptr in non_std_ptrs}

    # We don't know if these bytes are used or not
    # FIXME: just clip the last script
    if len(non_std_ptrs) > 0:
        scripts = {name: ptr for name, ptr in scripts.items()
                                           if name not in non_std_ptrs}

    # TODO: make the final pointer None and scan the end of the block to truncate
    # Define script boundaries
    script_ptrs = sorted(set(scripts.values()) | {0xFC050})
    script_ptrs = dict(zip(script_ptrs[:-1], script_ptrs[1:]))

    # Determine script blocks --- vanilla has one, but other modifications may introduce others
    script_blocks = [(min(script_ptrs.keys()), max(script_ptrs.values()))]

    invalid = {}
    #scripts = {v: k for k, v in scripts.items()}
    for i, name in enumerate(names):
        if name in non_std_ptrs:
            continue
        sptr, eptr = scripts[i], script_ptrs[scripts[i]]
        bin_script = romfile[sptr:eptr]
        try:
            scripting.Script.validate(bin_script, allow_empty_fc=True)
        except Exception as e:
            #raise ValueError(f"Script for {name} is invalid.")
            invalid[name] = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        s = scripting.Script.from_rom(sptr, eptr - sptr, name, romfile)
        #log.debug(f"{name} {s.name}\n{s.translate()}")
        # FIXME: obviated
        assert s.name == name, (s.name, name)
        assert s._bytes == bin_script

        scripts[name] = s

    # Handle scripts in nonstandard locations
    for name, ptr in non_std_ptrs.items():
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
            script = scripting.Script(_script, name, sptr)
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

        # See if this is a separate memory block
        linked_blks = [i for i, blk in enumerate(script_blocks) if blk[1] == ptr]
        if len(linked_blks) == 0:
            script_blocks.append((ptr, eptr))
            continue
        elif len(linked_blks) > 1:
            raise ValueError("Found possible overlapping set of scripts.")

        i = linked_blks[0]
        script_blocks[i] = (script_blocks[i][0], eptr)

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

    if return_blocks:
        return scripts, script_blocks
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

def extract(romfile=None, return_names=False):
    with open(romfile, "rb") as fin:
        romfile = fin.read()

    script_ptrs = extract_script_ptrs(romfile)
    # Canonical names
    names = extract_names(romfile, alias_duplicates=False)
    _names = [*range(len(names))]

    # Detect if BC has changed the scripts or their structure in some way
    is_bc = detect_bc(script_ptrs)
    log.info(f"ROM type: {'bc' if is_bc else 'vanilla'}")

    scripts, script_blocks = extract_scripts(romfile, script_ptrs, _names, return_blocks=True)

    # map script to canonical name
    #scripts = {n: scripts[idx] for idx, n in enumerate(_names)}

    if return_names:
        return scripts, names, script_blocks
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
