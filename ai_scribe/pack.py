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

if __name__ == "__main__":
    import os
    import random

    import command_graph
    from themes import AREA_SETS, STATUS_THEMES, ELEM_THEMES, BOSSES

    # Pick up all the structured commands
    scripts, names = extract(None, return_names=True)
    full_graph = command_graph.CommandGraph()
    full_graph.from_scripts({k: v._bytes for k, v in scripts.items()})

    batch = 8
    bdir = f"test_{batch:d}"
    os.mkdir(bdir)

    msg_id = 0

    fnames = [
        "FF3.1619405678.smc",
    ]

    for i in range(16):

        import numpy
        fname = numpy.random.choice(fnames)
        print(fname)
        with open(fname, "rb") as fin:
            romfile = fin.read()

        #scripts = extract(None)#fname)
        scripts, names = extract(None, return_names=True)

        script_length_orig = sum(map(len, scripts.values()))
        scr, ptrs = [], []
        mod_scripts = {}
        #for sset in AREA_SETS:
        for set_idx in range(len(AREA_SETS)):
            sset = AREA_SETS[set_idx]

            # We get a "window" around the current area, with one area lookback and two area lookforward
            sset = set.union(*AREA_SETS[max(set_idx-1, 0):min(set_idx+2, len(AREA_SETS))])

            cmd_graph = command_graph.CommandGraph()
            cmd_graph.from_scripts({k: v._bytes for k, v in scripts.items() if k in sset})

            # Allow for random messages
            cmd_graph.cmd_arg_graphs[0xF3] = full_graph.cmd_arg_graphs[0xF3]

            themes = ELEM_THEMES.copy()
            #themes.update(STATUS_THEMES)
            #themes = STATUS_THEMES.copy()
            aug_attacks = random.choice([*themes.values()])
            aug_attacks.add_edge(0xF0, list(aug_attacks.nodes)[0])

            # Randomize bosses
            bosses = sset & BOSSES
            DROP_EVENTS = {
                0x5, # Wedge and Vicks Whelk tutorial
                0x6, # M-M-M-M-MAGIC!? (TODO: could replace this with something else for the lulz
                #0x7, # This is a Vargas event, but unsure which
                0x8, # ??? I think this is the Blitz tutorial
                0x9, # post-pummel Vargas (TODO: same as above)
                #0xA, # Ultros1 post-battle
                0x10, # TunnelArmr opening scene
            }

            # FIXME: this removes a required link between commands, might need to replace it a placeholder
            #cmd_graph.cmd_arg_graphs[0xF7].remove_nodes_from(DROP_EVENTS)

            required = {0xFC, 0xF9, 0xF7, 0xFB}
            for name in bosses:
                bscr = cmd_graph.generate_from_template(scripts[name]._bytes,
                                                        required=required,
                                                        drop_events=DROP_EVENTS)

                diff = len(scripts[name])
                mod_scripts[name] = scripting.Script(bytes(bscr), name)
                diff -= len(scripts[name])
                #print(name, diff)

            # Drop "bosses" for now
            sset = sset - BOSSES
            # NOTE: we may want to somehow preserve them, but they keep injecting a lot of 0xFC into scripts

            cmd_graph = command_graph.CommandGraph()
            cmd_graph.from_scripts({k: v._bytes for k, v in scripts.items() if k in sset})

            # Spice goes here
            # Add in a random status/element theme
            #themes = ELEM_THEMES.copy()
            #themes.update(STATUS_THEMES)
            themes = STATUS_THEMES.copy()
            aug_attacks = random.choice([*themes.values()])
            aug_attacks.add_edge(0xF0, list(aug_attacks.nodes)[0])
            # FIXME: use augment
            cmd_graph.cmd_arg_graphs[0xF0] = \
                networkx.algorithms.compose(aug_attacks, cmd_graph.cmd_arg_graphs[0xF0])

            def edit_cmd_arg_graph(cmd_graph, drop_skills={}, drop_nothing=False):
                # remove "Nothing" from CHOOSE SPELL
                if drop_nothing:
                    cmd_graph.cmd_arg_graphs[0xF0].remove_nodes_from([0xFE])
                # remove "Escape" for now
                for cmd in {0xF0, "_"}:
                    cmd_graph.cmd_arg_graphs[cmd].remove_nodes_from(drop_skills)
            DROP_SKILLS = {
                0xC2, # escape
            }
            DROP_TARGETS = {

            }
            edit_cmd_arg_graph(cmd_graph, drop_skills=DROP_SKILLS)

            _scr, _ptrs = randomize_scripts(cmd_graph, n=len(sset), main_block_avg=2,
                                            disallow_commands={0xF7, 0xF2})

            # for funzies
            for j in range(len(_scr)):
                break
                _scr[j] = scripting.add_one_time_trigger(_scr[j],
                                                         [0xF3, msg_id % 256, 0x0, 0xFE])
                msg_id += 1

            diff = sum(len(scripts[name]) for name in sset)
            mod_scripts.update({k: scripting.Script(bytes(v), k) for k, v in zip(sset, _scr)})
            diff -= sum(len(mod_scripts[name]) for name in sset)
            #print(sset, diff)

        # Realign pointers
        scripts.update(mod_scripts)
        script_length_after = sum(map(len, scripts.values()))
        scr, ptrs = [], [0]
        for k in names:
            s = scripts.get(k, b"\xFF\xFF")
            if k not in scripts:
                print(k, "not found in script bank, appending empty script.")
            scr.append(s)
            ptrs.append(ptrs[-1] + len(scr[-1]))
            if ptrs[-1] >= 0xFC050 - 0xF8700:
                print("Pointer outside script block, overriding to last", k)
                ptrs[-1] = ptrs[-2]

        # Rewrite to address space
        low, hi = romfile[:0xF8400], romfile[0xFC050:]
        print(hex(len(low)), len(ptrs), len(scr))
        # Last one is superfluous
        for ptr in ptrs[:-1]:
            low += int.to_bytes(ptr, 2, byteorder="little")
        print(hex(len(low)), "== 0xF8700")

        for s in scr:
            low += bytes(s)
        print(hex(len(low)), "?= 0xFC050")
        low_block_diff = 0xFC050 - len(low)
        print(low_block_diff, script_length_orig - script_length_after)
        if low_block_diff > 0:
            print(f"Script block underrun, buffering {low_block_diff} bytes")
            low += bytes([255] * low_block_diff)
        elif low_block_diff < 0:
            print(f"Script block overrun, truncating {-low_block_diff} bytes")
            low = low[:0xFC050]
        print(hex(len(low)), "== 0xFC050")
        low += hi

        print(len(low), len(romfile))
        print(f"{bdir}/test.{batch}.{i}.smc")
        with open(f"{bdir}/test.{batch}.{i}.smc", "wb") as fout:
            fout.write(bytes(low))

        with open(f"{bdir}/test_scripts.{batch}.{i}.txt", "w") as fout:
            for n, s in scripts.items():
                # FIXME: insertion order still correct?
                print(n + "\n\n" + s.translate() + "\n", file=fout)
