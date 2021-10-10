import os
import glob
import math
import random
import numpy
import networkx.algorithms

import logging
logging.basicConfig()

from . import _NAME_ALIASES
from . import command_graph
from . import tableau_scripts, give_base_mp
from . import scripting
from .extract import *
from .extract import ScriptSet
from .pack import randomize_scripts
from .flags import ESPERS, DESPERATIONS

from .themes import AREA_SETS, STATUS_THEMES, ELEM_THEMES, BOSSES, EVENT_BATTLES

# We have to do this here or else the submodules will override it.
log = logging.getLogger("ai_scribe")
log.setLevel(logging.INFO)

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
                           f"(can be BC or vanilla ROM, default is {srcrom}): ")
        # Pick up all the structured commands
        srcrom = os.path.realpath(srcrom)
        log.info(f"Reading script data from {srcrom}")
        scripts, names = extract(srcrom, return_names=True)
    except OSError:
        log.error("The provided base script path didn't work, please try again or report as a bug.")
        exit()

    full_graph = command_graph.CommandGraph()
    full_graph.from_scripts({k: v._bytes for k, v in scripts.items()})

    #inpth = "base_roms" or input("Provide a path to either a folder with prerandomized ROMs, or a single "
    inpth = input("Provide a path to either a folder with prerandomized ROMs, or a single "
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

    # configuration
    conf = {
        # Randomization methodology
        # BC's name changes will confuse the area-base listing
        # randomization, so this will allow the method to continue
        # even if some of the scripts are "missing"
        # (actually named something else)
        "allow_missing_scripts": True,
        # Do not randomize
        "do_not_randomize": set(EVENT_BATTLES),
        # Banned skills / commands / events
        "drop_skills": {
            0x7D,  # Bio Blast / Super Ball
            0x7E,  # Flash
            0xC2,  # Escape
            0xC8,  # Seize
            0xEA,  # BabaBreath
            0xD5,  # Engulf --- NOTE: this only prevents other enemies from picking it up,
                   # Zone Eater is exempt from randomization
        } | set(ESPERS) | set(DESPERATIONS),
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
        # do we give weak enemies 20 MP minimum to use on skills?
        "give_min_mp": True,

        # number of retries for script generation failure
        "num_retries": 100,
        "batch_id": 9,
        "copies_per_batch": 16,
        #"random_seed": 0,

        # write out the base script file if not None
        #"write_base_scripts": "etc/script_dump.txt",
        "write_base_scripts": None,
        "script_dump_only": False,
    }

    random.seed(conf.get("random_seed", 0))
    numpy.random.seed(conf.get("random_seed", 0))

    if conf["write_base_scripts"] is not None:
        log.info(f"Writing base script translation to {conf['write_base_scripts']}")
        with open(conf["write_base_scripts"], "w") as fout:
            for i, (name, script) in enumerate(scripts.items()):
                print(f"{i}: {name}\n\n{script.translate()}\n", file=fout)
    if conf["script_dump_only"]:
        log.info("Script dump finished, exiting.")
        exit()

    # batching
    bdir = f"test_{conf['batch_id']:d}"
    #os.mkdir(bdir)

    for i in range(conf["copies_per_batch"]):
        # carry some additional metadata around
        _meta = {}

        fname = numpy.random.choice(fnames)
        log.debug(fname)
        with open(fname, "rb") as fin:
            romfile = fin.read()

        if conf["give_min_mp"]:
            log.info("Giving minimum MP to all enemies.")
            give_base_mp(romfile)

        # FIXME: do we need to re-read this? Probably not.
        scripts, names = extract(srcrom, return_names=True)
        log.info(f"Read {len(scripts)} total scripts from {srcrom}")
        # FIXME: Temporary --- while we read from one rom and
        # write to another (probably different seed) we'll
        # need the name order from that rom, as well as any
        # additional scripts which are encoded there. Once
        # we can handle everything smoothly, this should go away
        _scripts, _names = extract(fname, return_names=True)
        # TODO: update from BC
        if False:
            _scripts.update(scripts)
            scripts = _scripts

        scripts = ScriptSet(srcrom)

        #batt_msgs = extract_battle_msgs(srcrom)

        # tracks the marginal budget we have on free space
        extra_space = 0
        script_length_orig = sum(map(len, scripts.scripts.values()))
        log.debug((hex(script_length_orig), hex(0xFC050 - 0xF8700)))

        scr, ptrs = [], []
        mod_scripts = {}
        # FIXME: pointers for debugging purposes --- can remove when more confident
        t1, t2 = 0, 0
        for set_idx in range(len(AREA_SETS)):
            # Set of scripts to change (using names)
            sset = AREA_SETS[set_idx].copy()

            remove_from_pool = sset & conf["do_not_randomize"]
            for name in remove_from_pool:
                # Add offsets of scripts we won't change
                t1 += len(scripts[name]._bytes)
                t2 += len(scripts[name]._bytes)
            # NOTE: This means that none of their commands / skills are in the pool either (probably okay)
            sset -= remove_from_pool
            log.debug(f"The following scripts have been removed from the pool, by request: {', '.join(remove_from_pool)}")

            # We get a "window" around the current area, with one area lookback and two area lookforward
            pool = set.union(*AREA_SETS[max(set_idx-1, 0):min(set_idx+2, len(AREA_SETS))])

            # FIXME: we will eventually want to stop relying on the old dedup scheme
            pool = {n: scripts[n] for n in pool}
            log.debug(f"Formed pool of {len(pool)} scripts to use this iteration.")

            cmd_graph = command_graph.CommandGraph()
            cmd_graph.from_scripts({k: v._bytes for k, v in pool.items()})

            # Allow for random messages
            if conf["talkative"]:
                cmd_graph.cmd_arg_graphs[0xF3] = full_graph.cmd_arg_graphs[0xF3]

            # add a little spice
            command_graph.augment_cmd_graph(cmd_graph, status=conf["spice"]["boss_status"],
                                                       elemental=conf["spice"]["boss_elemental"])
            command_graph.edit_cmd_arg_graph(cmd_graph, drop_skills=conf["drop_skills"])
            log.debug(cmd_graph.to_text_repr())

            # Randomize bosses
            # FIXME: make flag for "allow bosses to be in pool" (currently true)
            bosses = sset & BOSSES

            # FIXME: this removes a required link between commands, might need to replace it a placeholder
            #cmd_graph.cmd_arg_graphs[0xF7].remove_nodes_from(conf["drop_events"])

            required = {0xFC, 0xF9, 0xF7, 0xFB, 0xF5}
            for name in bosses:
                # This only reduces the length from the original script
                bscr = cmd_graph.generate_from_template(pool[name]._bytes,
                                                        required=required,
                                                        drop_events=conf["drop_events"])

                mod_scripts[name] = scripting.Script(bytes(bscr), name)

                _meta[name] = "type: from template\n"
                _meta[name] += f"created from: {sset}\n"
                _meta[name] += cmd_graph.to_text_repr()

                extra_space += len(pool[name]._bytes) - len(mod_scripts[name]._bytes)
                log.debug(f"Randomizing boss {name} ({len(pool[name]._bytes)} vanilla bytes) "
                          f"to {len(mod_scripts[name]._bytes)} modified bytes.\n"
                          f"(Before) Vanilla ptr: {t1} [{hex(t1)}] | modified ptr: {t2} [{hex(t2)}]\n"
                          f"{len(mod_scripts)} modified script so far.")
                t1 += len(pool[name]._bytes)
                t2 += len(mod_scripts[name]._bytes)
                log.debug(f"(After) Vanilla ptr: {t1} [{hex(t1)}] | modified ptr: {t2} [{hex(t2)}]) "
                          f"| extra space {extra_space} [{hex(extra_space)}]")

                log.debug(f"--- {name} ---")
                log.debug(f"Created from {sset} + ")
                # Empty FC blocks can be inherited from the original script
                scripting.Script.validate(bytes(bscr), allow_empty_fc=True)
                assert len(mod_scripts[name]._bytes) >= 2 and len(pool[name]._bytes) >= 2
                log.debug("\n" + tableau_scripts(pool[name].translate(),
                                                 mod_scripts[name].translate()))

                assert len(pool[name]._bytes) >= len(mod_scripts[name]._bytes), (name, len(pool[name]._bytes),  len(mod_scripts[name]._bytes))

            cmd_graph = command_graph.CommandGraph()
            # NOTE: we may want to somehow preserve them, but they keep injecting a lot of 0xFC into scripts
            # Drop "bosses" for now
            cmd_graph.from_scripts({k: pool[k]._bytes for k in sset - BOSSES})

            # Spice goes here
            # Add in a random status/element theme
            command_graph.augment_cmd_graph(cmd_graph, status=conf["spice"]["normal_status"],
                                                       elemental=conf["spice"]["normal_elemental"])
            command_graph.edit_cmd_arg_graph(cmd_graph, drop_skills=conf["drop_skills"])
            assert 0xC2 not in cmd_graph.cmd_graph

            log.debug(cmd_graph.to_text_repr())

            for name in sset:
                _meta[name] = "type: from template\n"
                _meta[name] += f"created from: {sset}\n"
                _meta[name] += cmd_graph.to_text_repr()

            # bosses have already been randomized
            sset -= BOSSES

            # Total length of scripts + extra_space
            # extra_space is basically the offset from the vanilla pointer
            # it can be plus or minus
            total_len = sum(len(pool[name]) for name in sset) + extra_space
            # increment vanilla pointer
            t1 += total_len - extra_space

            main_block_avg = max(int(math.log2(max(total_len, 1) + extra_space) / max(1, len(sset))), 1)
            # disallow commands and strict can cause conflicts
            gen_kwargs = {"disallow_commands": {0xF7, 0xF2},
                          "naborts": conf["num_retries"], "strict": False}
            _scr, _ptrs = randomize_scripts(cmd_graph, n=len(sset),
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
            log.debug(" | ".join(map(str, (hex(t1), hex(t2), (t2 - t1), sum(map(len, _scr)),total_len, extra_space, sset))))

            # This means that the enemy has been randomized more than once. In the interests of keeping
            # bookkeeping more simple, we'll just explicitly disallow this for now
            #assert len(set(_sset & set(mod_scripts.keys()))) == 0, set(_sset & set(mod_scripts))
            already_processed = set(sset & set(mod_scripts))
            if len(already_processed) > 0:
                log.warning(f"{already_processed} already randomized, and will be skipped this time.")
            #assert len(already_processed) == 0, already_processed
            mod_scripts.update({k: scripting.Script(bytes(v), k)
                                    for k, v in zip(sset, _scr) if k not in mod_scripts})

            for name in sset:
                log.debug(f"--- {name} ---")
                log.debug(f"Created from {sset} + ")
                scripting.Script.validate(mod_scripts[name]._bytes)
                log.debug("\n" + tableau_scripts(pool[name].translate(),
                                                 mod_scripts[name].translate()))

        # FIXME: move to pack module
        # Realign pointers
        export = scripts.get_ordered_script_array()
        for n, s in mod_scripts.items():
            export[scripts._get_index(n)] = s
        script_length_after = sum(map(len, export))
        logging.debug(hex(0xFC050 - 0xF8700), hex(script_length_after))

        # Split the enemies into scripts that need to be written
        # first, so as to not soft-lock the game at some point
        # because of truncation
        write_first = set(identify_special_event_scripts(scripts.scripts))
        write_first |= {scripts._get_index(n) for n in BOSSES | conf["do_not_randomize"]}
        #if is_bc
        #write_first = {scripts._get_index(n) for n in write_first}

        from ai_scribe import pack
        scr, ptrs = pack.pack_scripts(export, names, write_first)

        # Rewrite to address space
        low, hi = romfile[:0xF8400], romfile[0xFC050:]
        log.debug((hex(len(low)), len(ptrs), len(scr), len(names)))
        for ptr in ptrs:
            low += int.to_bytes(ptr, 2, byteorder="little")
        log.debug((hex(len(low)), "== 0xF8700"))

        for s in scr:
            low += bytes(s)
        log.debug((hex(len(low)), "?= 0xFC050"))
        low_block_diff = 0xFC050 - len(low)
        log.debug((low_block_diff, script_length_orig - script_length_after))
        if low_block_diff > 0:
            log.debug(f"Script block underrun, buffering {low_block_diff} bytes")
            low += bytes([255] * low_block_diff)
        elif low_block_diff < 0:
            log.debug(f"Script block overrun, truncating {-low_block_diff} bytes")
            low = low[:0xFC050]
        log.debug((hex(len(low)), "== 0xFC050"))
        assert len(low) == 0xFC050
        low += hi

        log.debug((len(low), len(romfile)))
        outfname = f"{bdir}/test.{conf['batch_id']}.{i}.smc"
        with open(outfname, "wb") as fout:
            fout.write(bytes(low))
        log.info(f"Generated ROM at {outfname}")

        spoiler = f"{bdir}/test.{conf['batch_id']}.{i}.txt"
        with open(spoiler, "w") as fout:
            for n, s in zip(names, export):
                _n = _NAME_ALIASES.get(n, n)
                print(f"--- {_n} ---", file=fout)
                if n in _meta:
                    print(_meta[n], file=fout)

                print(f"Original | Randomized", file=fout)
                if n in mod_scripts:
                    print(tableau_scripts(scripts[n].translate(),
                                          mod_scripts[n].translate()), file=fout)
                else:
                    print(tableau_scripts(scripts[n].translate(),
                                          "NO SCRIPT RANDOMIZATION"), file=fout)
                print("", file=fout)
        log.info(f"Generated script spoiler at {bdir}/test_scripts.{conf['batch_id']}.{i}.txt")

        #if conf['verify_rom']:
        if True:
            log.info(f"Rechecking and verifying {outfname}")
            outfname = os.path.realpath(outfname)
            new_scripts, new_names = extract(outfname, return_names=True, force_bc=True)
            for n, scr in new_scripts.items():
                #assert scr._bytes == export[n]._bytes, n
                if scr._bytes != export[n]._bytes:
                    #print(n, scr._bytes, export[n]._bytes)
                    print(f"DIFFERENCE: {n}")
                    print(tableau_scripts(scr.translate(), export[n].translate()))
