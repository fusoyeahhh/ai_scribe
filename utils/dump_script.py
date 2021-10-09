import os
import argparse

import logging
logging.basicConfig()

log = logging.getLogger("ai_scribe")

#from ai_scribe import tableau_scripts
from ai_scribe.extract import extract

argp = argparse.ArgumentParser()

argp.add_argument("-p", "--path-to-rom",
                  help="(required) Path to ROM file to dump scripts from.")
argp.add_argument("-o", "--out-path", default='script_dump.txt',
                  help="Path to dump scripts to, default is 'script_dump.txt'.")
argp.add_argument("-l", "--list-names", action='store_true',
                  help="List the names in the order they appear in the game's index.")
argp.add_argument("-s", "--print-scripts", action='append',
                  help="Print only these scripts to the console.")
_ALLOWED_LEVELS = ", ".join(logging._nameToLevel)
argp.add_argument("-L", "--log-level", default='INFO',
                  help=f"Set the log level. Default is INFO. Available choices are {_ALLOWED_LEVELS}.")

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
    scripts, names = extract(src, return_names=True)
    log.info(f"Found {len(scripts)} scripts")

    # Print only the names with their lookup order
    if args.list_names:
        for name in names:
            outstr = " ".join([f'({str(i).rjust(3)}) {n.ljust(12)}' for i, n in enumerate(names)])
            while outstr:
                print(outstr[:19 * 4])
                outstr = outstr[19 * 4:]
            exit()

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
