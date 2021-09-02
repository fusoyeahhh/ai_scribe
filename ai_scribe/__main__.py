import os
import glob
import math
import random
import numpy
import networkx.algorithms

import logging
log = logging.getLogger("ai_scribe")
log.setLevel("INFO")

from . import command_graph
from . import scripting
from .extract import *
from .pack import _validate, randomize_scripts

from .themes import AREA_SETS, STATUS_THEMES, ELEM_THEMES, BOSSES

if __name__ == "__main__":

    log.warning("This is a PRERELEASE version of the AI Scribe for FFVI. There are no guarantees that the produced game "
          "is fully completable or functional. This is for testing purposes only. Currently, it is known that this "
          "version is mostly compatible with Beyond Chaos, though due to memory addressing issues, later bosses and "
          "final Kefka are likely to be buggy.")

    srcrom = "Final Fantasy III (U) (V1.0) [!].smc"
    try:
        if not os.path.exists(srcrom):
            srcrom = input(f"Provide a path to a V1.0 English ROM (same as used for BC, default is {srcrom}): ")
        # Pick up all the structured commands
        srcrom = os.path.realpath(srcrom)
        log.info(f"Reading script data from {srcrom}")
        scripts, names = extract(srcrom, return_names=True)
    except OSError:
        log.error("One or more of the provided paths didn't work, please try again or report as a bug.")
        exit()

    full_graph = command_graph.CommandGraph()
    full_graph.from_scripts({k: v._bytes for k, v in scripts.items()})

    inpth = "base_roms" or input("Provide a path to either a folder with prerandomized ROMs, or a single "
                  "(vanilla or otherwise) ROM: ") or "base_roms"
    if not os.path.exists(inpth):
        log.error("One or more of the provided paths didn't work, please try again or report as a bug.")
        exit()

    if os.path.isdir(inpth):
        fnames = glob.glob(os.path.join(inpth, "*.smc"))
    else:
        fnames = [inpth]

    if len(fnames) == 0:
        log.error("One or more of the provided paths didn't work, please try again or report as a bug.")
        exit()
    log.info(f"Found {len(fnames):d} ROMs")

    # batching
    batch = 9
    bdir = f"test_{batch:d}"
    #os.mkdir(bdir)

    prefix = "test"
    prefix = prefix or input(f"Enter a name for the new ROM (default {prefix})")

    for i in range(16):

        fname = numpy.random.choice(fnames)
        log.debug(fname)
        with open(fname, "rb") as fin:
            romfile = fin.read()

        scripts, names = extract(srcrom, return_names=True)

        # tracks the marginal budget we have on free space
        extra_space = 0
        log.debug(hex(sum(map(len, scripts.values()))), hex(0xFC050 - 0xF8700))

        script_length_orig = sum(map(len, scripts.values()))
        scr, ptrs = [], []
        mod_scripts = {}
        # FIXME: pointers for debugging purposes --- can remove when more confident
        t1, t2 = 0, 0
        for set_idx in range(len(AREA_SETS)):
            # Set of scripts to change
            _sset = AREA_SETS[set_idx]

            # We get a "window" around the current area, with one area lookback and two area lookforward
            sset = set.union(*AREA_SETS[max(set_idx-1, 0):min(set_idx+2, len(AREA_SETS))])

            # Check to make sure we cover all the enemies in the set with scripts
            omitted = sset - set(scripts.keys())
            if omitted:
                raise ValueError("Found enemies in requested change list "
                                 "which has no corresponding vanilla script: "
                                 f"{omitted}")

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
            bosses = _sset & BOSSES
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
                # This only reduces the length from the original script
                bscr = cmd_graph.generate_from_template(scripts[name]._bytes,
                                                        required=required,
                                                        drop_events=DROP_EVENTS)

                mod_scripts[name] = scripting.Script(bytes(bscr), name)
                extra_space += len(scripts[name]._bytes) - len(mod_scripts[name]._bytes)
                log.debug(f"Randomizing boss {name} ({len(scripts[name]._bytes)} vanilla bytes) "
                          f"to {len(mod_scripts[name]._bytes)} modified bytes.\n"
                          f"(Before) Vanilla ptr: {t1} [{hex(t1)}] | modified ptr: {t2} [{hex(t2)}]\n"
                          f"{len(mod_scripts)} modified script so far.")
                t1 += len(scripts[name]._bytes)
                t2 += len(mod_scripts[name]._bytes)
                log.debug(f"(After) Vanilla ptr: {t1} [{hex(t1)}] | modified ptr: {t2} [{hex(t2)}]) "
                          f"| extra space {extra_space} [{hex(extra_space)}]")

                from . import tableau_scripts
                print("---", name, "---")
                print(f"Created from {sset} + ")
                print(tableau_scripts(scripts[name].translate(),
                                      mod_scripts[name].translate()))

                assert len(scripts[name]._bytes) >= len(mod_scripts[name]._bytes), (name, len(scripts[name]._bytes),  len(mod_scripts[name]._bytes))

            cmd_graph = command_graph.CommandGraph()
            # NOTE: we may want to somehow preserve them, but they keep injecting a lot of 0xFC into scripts
            # Drop "bosses" for now
            cmd_graph.from_scripts({k: scripts[k]._bytes for k in sset - BOSSES})

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

            # bosses have already been randomized
            _sset -= BOSSES

            # Total length of scripts + extra_space
            # extra_space is basically the offset from the vanilla pointer
            # it can be plus or minus
            total_len = sum(len(scripts[name]) for name in _sset) + extra_space
            # increment vanilla pointer
            t1 += total_len - extra_space

            main_block_avg = max(int(math.log2(max(total_len, 1) + extra_space) / max(1, len(_sset))), 1)
            gen_kwargs = {"disallow_commands": {0xF7, 0xF2}}
            _scr, _ptrs = randomize_scripts(cmd_graph, n=len(_sset),
                                            #main_block_avg=main_block_avg,
                                            main_block_avg=5,
                                            total_len=total_len, **gen_kwargs)
            assert sum(map(len, _scr)) <= total_len, "Script block length exceeds request."

            # DEBUG
            #for name, scr in zip(_sset, _scr):
                #print(f"{name}: {len(scripts[name])} -> {len(scr)}")
            #print(f"block length: {total_len} -> {sum(map(len, _scr))}")

            # increment modified script pointer
            t2 += sum(map(len, _scr))
            extra_space = total_len - sum(map(len, _scr))
            log.debug("v. ptr | m. ptr | ptr diff | total m. bytes | allowed m. bytes | extra | m. set")
            log.debug(hex(t1), hex(t2), (t2 - t1), sum(map(len, _scr)), total_len, extra_space, _sset)

            # This means that the enemy has been randomized more than once. In the interests of keeping
            # bookkeeping more simple, we'll just explicitly disallow this for now
            #assert len(set(_sset & set(mod_scripts.keys()))) == 0, set(_sset & set(mod_scripts))
            already_processed = set(_sset & set(mod_scripts))
            if len(already_processed) > 0:
                log.warning(f"{already_processed} already randomized, and will be skipped this time.")
            #assert len(already_processed) == 0, already_processed
            mod_scripts.update({k: scripting.Script(bytes(v), k) for k, v in zip(_sset, _scr) if k not in mod_scripts})

        # Realign pointers
        scripts.update(mod_scripts)
        script_length_after = sum(map(len, scripts.values()))
        logging.debug(hex(0xFC050 - 0xF8700), hex(script_length_after))
        scr, ptrs = [], [0]
        for k in names:
            s = scripts.get(k, b"\xFF\xFF")
            if k not in scripts:
                log.warning(k, "not found in script bank, appending empty script.")
            scr.append(s)
            ptrs.append(ptrs[-1] + len(scr[-1]))
            if ptrs[-1] >= 0xFC050 - 0xF8700:
                log.warning(f"Pointer outside script block, overriding to last {k}")
                ptrs[-1] = ptrs[-2]

        # Rewrite to address space
        low, hi = romfile[:0xF8400], romfile[0xFC050:]
        log.debug(hex(len(low)), len(ptrs), len(scr), len(names))
        # Last one is superfluous
        for ptr in ptrs[:-1]:
            low += int.to_bytes(ptr, 2, byteorder="little")
        log.debug(hex(len(low)), "== 0xF8700")

        for s in scr:
            low += bytes(s)
        log.debug(hex(len(low)), "?= 0xFC050")
        low_block_diff = 0xFC050 - len(low)
        log.debug(low_block_diff, script_length_orig - script_length_after)
        if low_block_diff > 0:
            log.debug(f"Script block underrun, buffering {low_block_diff} bytes")
            low += bytes([255] * low_block_diff)
        elif low_block_diff < 0:
            log.debug(f"Script block overrun, truncating {-low_block_diff} bytes")
            low = low[:0xFC050]
        log.debug(hex(len(low)), "== 0xFC050")
        assert len(low) == 0xFC050
        low += hi

        log.debug(len(low), len(romfile))
        with open(f"{bdir}/test.{batch}.{i}.smc", "wb") as fout:
            fout.write(bytes(low))
        log.info(f"Generated ROM at {bdir}/test.{batch}.{i}.smc")

        with open(f"{bdir}/test_scripts.{batch}.{i}.txt", "w") as fout:
            for n, s in scripts.items():
                # FIXME: insertion order still correct?
                print(n + "\n\n" + s.translate() + "\n", file=fout)
        log.info(f"Generated script spoiler at {bdir}/test_scripts.{batch}.{i}.txt")
