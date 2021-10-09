import os
import math
import argparse

import logging
logging.basicConfig()

log = logging.getLogger("ai_scribe")

#from ai_scribe import tableau_scripts
from ai_scribe import _NAME_ALIASES
from ai_scribe.extract import extract, extract_names

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
                  help="Print only these scripts to the console.")
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

    # Print only the names with their lookup order
    if args.list_names:
        names = extract_names(src, alias_duplicates=args.alias_duplicates)
        if args.alias_duplicates:
            names = [_NAME_ALIASES.get(n, n) for n in names]

        base = 34 if args.alias_duplicates else 12
        n_per_line = 2 if args.alias_duplicates else 4

        outstr, i = [], 0
        for _ in range(int(math.ceil(len(names) / n_per_line))):
            chunk, names = names[:n_per_line], names[n_per_line:]
            idx = [f"({str(j).rjust(3)})" for j in range(i, i + n_per_line)]
            i += n_per_line
            outstr.append(" ".join([f'{j} {n[:base].ljust(base)}' for j, n in zip(idx, chunk)]))

        print("\n".join(outstr))
        exit()

    scripts, names = extract(src, return_names=True)
    log.info(f"Found {len(scripts)} scripts")

    # Print only a selection of scripts
    if args.print_scripts and len(args.print_scripts) > 0:
        for name in args.print_scripts:
            if name not in scripts:
                log.error(f"{name} not in ROM, skipping")
                continue
            print(f"{name}\n\n{scripts[name].translate()}\n")
        exit()

    # Print the whole script block to a file
    log.info(f"Writing translation to {dst}")
    with open(dst, "w") as fout:
        for i, (name, script) in enumerate(scripts.items()):
            print(f"{i}: {name}\n\n{script.translate()}\n", file=fout)
