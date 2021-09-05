import os
import glob
import math
import random
import numpy
import networkx.algorithms

import logging
logging.basicConfig()
log = logging.getLogger("ai_scribe")
log.setLevel(logging.INFO)

from . import command_graph
from . import tableau_scripts
from . import scripting
from .extract import *
from .pack import randomize_scripts

from .themes import AREA_SETS, STATUS_THEMES, ELEM_THEMES, BOSSES

if __name__ == "__main__":

    log.warning("This is a PRERELEASE version of the AI Scribe for FFVI. There are no guarantees that the produced game "
          "is fully completable or functional. This is for testing purposes only. Currently, it is known that this "
          "version is mostly compatible with Beyond Chaos, though due to memory addressing issues, later bosses and "
          "final Kefka are likely to be buggy.")

    srcrom = "Final Fantasy III (U) (V1.0) [!].smc"
    try:
        if not os.path.exists(srcrom):
            #srcrom = input(f"Provide a path to a V1.0 English ROM (same as used for BC, default is {srcrom}): ")
            srcrom = input(f"Provide a path to a V1.0 English ROM for the base scripts."
                           "(can be BC or vanilla ROM, default is {srcrom}): ")
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

    prefix = "test"
    prefix = prefix or input(f"Enter a name for the new ROM (default {prefix})")

    # configuration
    conf = {
        # Randomization methodology
        # BC's name changes will confuse the area-base listing
        # randomization, so this will allow the method to continue
        # even if some of the scripts are "missing"
        # (actually named something else)
        "allow_missing_scripts": True,
        # Banned skills / commands / events
        "drop_skills": {
            0xC2,  # escape
        },
        "drop_events": {
            0x5,  # Wedge and Vicks Whelk tutorial
            0x6,  # M-M-M-M-MAGIC!? (TODO: could replace this with something else for the lulz
            # 0x7, # This is a Vargas event, but unsure which
            0x8,  # ??? I think this is the Blitz tutorial
            0x9,  # post-pummel Vargas (TODO: same as above)
            # 0xA, # Ultros1 post-battle
            0x10,  # TunnelArmr opening scene
        },
        "drop_targets": {},

        # SPICE
        "spice": {
            # will pick a random element and merge in random elemental attacks from category
            "boss_elemental": True,
            # will pick a random status and merge in random status attacks from category
            "boss_status": False,
            # will pick a random element and merge in random elemental attacks from category
            "normal_elemental": False,
            # will pick a random status and merge in random status attacks from category
            "normal_status": True,
        },

        # AI behavior modification
        # enemies already with events may have them swapped with others
        # the 'drop_events' configuration above is still respected
        "talkative": True,

        "batch_id": 9,
        "copies_per_batch": 16,

        # write out the base script file if not None
        #"write_base_scripts": "script_dump.txt",
         "write_base_scripts": None,
    }

    if conf["write_base_scripts"] is not None:
        with open(conf["write_base_scripts"], "w") as fout:
            for i, (name, script) in enumerate(scripts.items()):
                print(f"{i}: {name}\n\n{script.translate()}\n", file=fout)

    # batching
    bdir = f"test_{conf['batch_id']:d}"
    #os.mkdir(bdir)

    for i in range(conf["copies_per_batch"]):

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

            # FIXME: BC renaming is responsible for the filter, could interfere weirdly with vanilla
            _sset &= set(scripts.keys())

            # We get a "window" around the current area, with one area lookback and two area lookforward
            sset = set.union(*AREA_SETS[max(set_idx-1, 0):min(set_idx+2, len(AREA_SETS))])

            # Check to make sure we cover all the enemies in the set with scripts
            omitted = sset - set(scripts.keys())
            if omitted and conf["allow_missing_scripts"]:
                log.warning("Found enemies in requested change list "
                            "which has no corresponding vanilla script: "
                            f"{omitted}")
            elif omitted:
                raise ValueError("Found enemies in requested change list "
                                 "which has no corresponding vanilla script: "
                                 f"{omitted}")

            # FIXME: BC renaming is responsible for the filter, could interfere weirdly with vanilla
            _sset &= set(scripts.keys())
            sset &= set(scripts.keys())

            cmd_graph = command_graph.CommandGraph()
            cmd_graph.from_scripts({k: v._bytes for k, v in scripts.items() if k in sset})

            # Allow for random messages
            if conf["talkative"]:
                cmd_graph.cmd_arg_graphs[0xF3] = full_graph.cmd_arg_graphs[0xF3]

            # add a little spice
            command_graph.augment_cmd_graph(cmd_graph, status=conf["spice"]["boss_status"],
                                                       elemental=conf["spice"]["boss_elemental"])

            # Randomize bosses
            bosses = _sset & BOSSES

            # FIXME: this removes a required link between commands, might need to replace it a placeholder
            #cmd_graph.cmd_arg_graphs[0xF7].remove_nodes_from(conf["drop_events"])

            required = {0xFC, 0xF9, 0xF7, 0xFB}
            for name in bosses:
                # This only reduces the length from the original script
                bscr = cmd_graph.generate_from_template(scripts[name]._bytes,
                                                        required=required,
                                                        drop_events=conf["drop_events"])

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

                log.info(f"--- {name} ---")
                log.info(f"Created from {sset} + ")
                scripting.Script.validate(bytes(bscr))
                assert len(mod_scripts[name]._bytes) >= 2 and len(scripts[name]._bytes) >= 2
                log.info("\n" + tableau_scripts(scripts[name].translate(),
                                                mod_scripts[name].translate()))

                assert len(scripts[name]._bytes) >= len(mod_scripts[name]._bytes), (name, len(scripts[name]._bytes),  len(mod_scripts[name]._bytes))

            cmd_graph = command_graph.CommandGraph()
            # NOTE: we may want to somehow preserve them, but they keep injecting a lot of 0xFC into scripts
            # Drop "bosses" for now
            cmd_graph.from_scripts({k: scripts[k]._bytes for k in sset - BOSSES})

            # Spice goes here
            # Add in a random status/element theme
            command_graph.augment_cmd_graph(cmd_graph, status=conf["spice"]["normal_status"],
                                                       elemental=conf["spice"]["normal_elemental"])
            command_graph.edit_cmd_arg_graph(cmd_graph, drop_skills=conf["drop_skills"])
            assert 0xC2 not in cmd_graph.cmd_graph

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

            for name in _sset:
                log.info(f"--- {name} ---")
                log.info(f"Created from {_sset} + ")
                scripting.Script.validate(mod_scripts[name]._bytes)
                log.info("\n" + tableau_scripts(scripts[name].translate(),
                                                mod_scripts[name].translate()))

        # Realign pointers
        export = scripts.copy()
        export.update(mod_scripts)
        script_length_after = sum(map(len, export.values()))
        logging.debug(hex(0xFC050 - 0xF8700), hex(script_length_after))
        scr, ptrs = [], [0]
        for k in names:
            s = export.get(k, b"\xFF\xFF")
            if k not in export:
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
        with open(f"{bdir}/test.{conf['batch_id']}.{i}.smc", "wb") as fout:
            fout.write(bytes(low))
        log.info(f"Generated ROM at {bdir}/test.{conf['batch_id']}.{i}.smc")

        with open(f"{bdir}/test_scripts.{conf['batch_id']}.{i}.txt", "w") as fout:
            for n, s in scripts.items():
                #print(n + "\n\n" + s.translate() + "\n", file=fout)
                print(f"--- {n} ---", file=fout)
                print(f"Randomized | Original", file=fout)
                #print(f"Created from {sset}", file=fout)
                if n in mod_scripts:
                    print(tableau_scripts(scripts[n].translate(),
                                          mod_scripts[n].translate()), file=fout)
                else:
                    print(tableau_scripts(scripts[n].translate(),
                                          "NO SCRIPT RANDOMIZATION"), file=fout)
                print("", file=fout)
        log.info(f"Generated script spoiler at {bdir}/test_scripts.{conf['batch_id']}.{i}.txt")
