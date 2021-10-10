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
    scripts, names = extract.extract(src, return_names=True)
    log.info(f"Found {len(scripts)} scripts")

    if args.verify_scripts:
        log.info(f"Verifying {src}")
        # Ensure all events are present and in the correct places
        special_events = extract.identify_special_event_scripts(scripts)
        for event, sid in special_events.items():
            print(f"{sid}: {flags.SPECIAL_EVENTS[event]} ({hex(event)})")
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
            i += n_per_line
            outstr.append(" ".join([f'{j} {(n + a)[:base].ljust(base)}'
                                        for j, n, a in zip(idx, chunk, aliases)]))

        print("Script pointers are relative to 0xF8700")
        print("\n".join(outstr))
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
            print(f"{_name}\n\n{scripts[name].translate()}")
        exit()

    # Print the whole script block to a file
    log.info(f"Writing translation to {dst}")
    with open(dst, "w") as fout:
        for i, (name, script) in enumerate(scripts.items()):
            print(f"{i}: {names[i]}\n\n{script.translate()}\n", file=fout)
    log.info(f"Done")
