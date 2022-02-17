import os
import math
import argparse

import logging
logging.basicConfig()

log = logging.getLogger("ai_scribe")

#from ai_scribe import tableau_scripts
from ai_scribe import _NAME_ALIASES
from ai_scribe import extract
from ai_scribe import flags

argp = argparse.ArgumentParser()

argp.add_argument("-p", "--path-to-rom",
                  help="(required) Path to ROM file to dump scripts from.")
argp.add_argument("-o", "--out-path", default='script_dump.txt',
                  help="Path to dump scripts to, default is 'script_dump.txt'.")
argp.add_argument("-l", "--list-names", action='store_true',
                  help="List the names in the order they appear in the game's index.")
argp.add_argument("-a", "--alias-duplicates", action='store_true', default=False,
                  help="Alias duplicate names in list (e.g. blank names), default is false.")
argp.add_argument("-f", "--filter-name", action="append",
                  help="Filter scripts for this pattern, when given with -l")
argp.add_argument("-s", "--print-scripts", action='append',
                  help="Print only these scripts to the console. Will select by order if integer is given.")
argp.add_argument("-V", "--verify-scripts", action='store_true',
                  help="Do some verification checks on the scripts.")
_ALLOWED_LEVELS = ", ".join(logging._nameToLevel)
argp.add_argument("-L", "--log-level", default='WARN',
                  help=f"Set the log level. Default is WARN. Available choices are {_ALLOWED_LEVELS}.")

if __name__ == "__main__":
    args = argp.parse_args()
    # set logging
    log.setLevel(args.log_level.upper())

    src, dst = args.path_to_rom, args.out_path
    if src is None:
        exit("Specify path to ROM with '-p'")
    if not os.path.exists(src):
        exit(f"Path {src} does not exist.")

    log.info(f"Reading {src}")
    scripts, names, blks = extract.extract(src, return_names=True)
    log.info(f"Found {len(scripts)} scripts")

    if args.verify_scripts:
        log.info(f"Verifying {src}")
        print("--- SPECIAL ANIMATIONS ---")
        alts = extract.identify_special_animations(scripts)
        # FIXME: there can be more than one
        for sid, (anim, targ, unkn) in alts.items():
            name = names[sid]
            anim = flags.ANIMATIONS[anim]
            targs = [i for i in range(8) if i & (1 << i)]
            targs = "self" if len(targs) == 0 else "{" + ", ".join(targs) + "}"
            print(f"{name} ({sid}):\n\t{targs} {anim} with unknown byte val {unkn}")

        # Check on formation alterations and changes
        print("--- FORMATION ALTERATIONS ---")
        alts = extract.identify_formation_alterations(scripts)
        # FIXME: there can be more than one
        for sid, (anim, act, targ) in alts.items():
            name = names[sid]
            FORM_ALT = {
                0: "UNHIDE AT MAX HP",
                1: "KILLED",
                2: "UNHIDE AT CUR HP",
                3: "HIDE AT MAX HP",
                4: "HIDE AT CUR HP",
            }
            act = FORM_ALT.get(act, "???")
            try:
                anim = flags.ENT_ANIMATIONS[anim]
            except IndexError:
                anim = f"UNKNOWN ({anim})"
            targs = [i for i in range(8) if i & (1 << i)]
            targs = "self" if len(targs) == 0 else "{" + ", ".join(targs) + "}"
            print(f"{name} ({sid}):\n\t{act} {targs} with animation {anim}")

        print("--- FORMATION CHANGES ---")
        changes = extract.identify_formation_swaps(scripts)
        for sid, chng in changes.items():
            name = names[sid]
            to_form = 0x100 * chng[2] + chng[1]
            max_hp = (to_form & 0x8000) == 0x8000
            to_form = ((to_form << 1) & 0xFFF) >> 1
            print(f"{name} ({sid}):\n\tunknown, should be zero: {chng[0]} to form {to_form} with max hp? {max_hp}")

        # Ensure all events are present and in the correct places
        special_events = extract.identify_special_event_scripts(scripts)
        print("--- SPECIAL EVENTS ---")
        for event, sid in special_events.items():
            name = names[sid]
            print(f"{name} ({sid}): {flags.SPECIAL_EVENTS[event]} ({hex(event)})")
        # NOTE: identify only gets one event per script, so script managers
        # may not be fully represented here (E.g. Kefka, Vargas, etc...)
        if len(special_events) < 15:
            exit("The required number of special event bytes is not present.")
        exit()

    # Print only the names with their lookup order and metadata
    if args.list_names:
        # Internal aliases
        names = extract.extract_names(src, alias_duplicates=False)

        ptrs = extract.extract_script_ptrs(src)

        base = 34 if args.alias_duplicates else 12
        n_per_line = 2 if args.alias_duplicates else 3

        outstr, i = [], 0
        args.filter_name = set(args.filter_name or [])
        for _ in range(int(math.ceil(len(names) / n_per_line))):
            chunk, names = names[:n_per_line], names[n_per_line:]

            idx = [j for j in range(i, i + n_per_line)]
            aliases = [f" ({_NAME_ALIASES[j]})" if j in _NAME_ALIASES and args.alias_duplicates else ""
                       for j, n in zip(idx, chunk)]
            # for n in _chunk]
            idx = [str(j).rjust(3) + ":"
                   + (f"{hex(ptrs[j] - 0xF8700)}+{hex(len(scripts[j]))}").ljust(12)
                   for j in idx]
            idx = [f"[{prefix}]" for prefix in idx]

            matches = {name for name in names if any({fname for fname in args.filter_name if fname in name})}
            keep = {j for j, name in enumerate(chunk)
                                       if args.filter_name is None or name in matches}
            matches = {name for name in aliases if any({fname for fname in args.filter_name if fname in name})}
            keep |= {j for j, name in enumerate(aliases)
                                        if args.filter_name is None or name in matches}
            i += n_per_line
            outstr.append(" ".join([f'{j} {(n + a)[:base].ljust(base)}'
                                for k, (j, n, a) in enumerate(zip(idx, chunk, aliases)) if k in keep]))

        print("Detected the following script blocks:")
        for (lo, hi) in blks:
            print(f"{hex(lo)} -- {hex(hi)}")
        print("Script pointers are relative to 0xF8700")
        print("\n".join([s for s in outstr if s]))
        exit()

    # Print only a selection of scripts
    if args.print_scripts and len(args.print_scripts) > 0:
        names = extract.extract_names(src, alias_duplicates=False)
        for _name in args.print_scripts:
            name = None
            try:
                name = names.index(_name)
            except ValueError:
                pass
            try:
                name = name if name is not None else int(_name)
            except ValueError:
                # If this triggers, it's because it's not a parseable integer
                # and it's not an addressable name
                log.error(f"{_name} not in ROM, skipping")
                continue

            print(f"{_name} -> {name}")
            p = scripts[name].ptr
            print(f"Script pointer | absolute: {hex(p)}, relative: {hex(p - 0xF8700)}")
            print(f"{_name}\n\n{scripts[name].translate()}")
        exit()

    # Print the whole script block to a file
    log.info(f"Writing translation to {dst}")
    with open(dst, "w") as fout:
        for i, (name, script) in enumerate(scripts.items()):
            try:
                name = names[name]
            except IndexError:
                name = names[i]
            print(f"{i}: {name}\n\n{script.translate()}\n", file=fout)
    log.info(f"Done")
