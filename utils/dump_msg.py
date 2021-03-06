import os
import logging
logging.basicConfig()

from ai_scribe import extract

log = logging.getLogger("ai_scribe")


# Upper case
_CHARS = {128 + i: chr(j) for i, j in enumerate(range(65, 65 + 26))}
# Lower case
_CHARS.update({154 + i: chr(j) for i, j in enumerate(range(97, 97 + 26))})
# Numbers
_CHARS.update({180 + i: chr(j) for i, j in enumerate(range(48, 48 + 10))})
# FIXME: Will probably need symbols at some point
_CHARS[190] = "!"
_CHARS[191] = "?"
_CHARS[193] = ":"
_CHARS[195] = "'"
_CHARS[196] = "-"
_CHARS[197] = "."
_CHARS[198] = ","
_CHARS[0xd3] = "["
_CHARS[0xc2] = "]"
_CHARS[199] = "..." # ellipsis character
_CHARS[255] = ""

_CTRL = {
    # terminator sequence
    0: "|",
    # newline
    1: "\n",
    # pause?
    255: "<PAUSE>",
}

def translate(word, batt_msg=False):
    """
    Translate integer values to the FF6 character equivalents. Drops any value which does not have a character mapping.

    Numbers from https://github.com/subtractionsoup/beyondchaos/blob/master/tables/dialoguetext.txt

    :param word: list of integers to convert
    :return: string translation
    """
    if batt_msg:
        chars = _CHARS.copy()
        # 0xFF is space in this scheme
        chars[255] = " "
        chars[124] = "|"
        chars[10] = "\n"
        # not sure what this is, some type of control character
        chars[1] = ""

        trns = []
        _word = [*word]
        while len(_word) > 0:
            c = _word.pop(0)

            # Referring to a slot name
            if c == 2:
                c = _word.pop(0)
                trns.append(_CTRL.get(c, f"[SLOT {c} NAME]"))
                continue

            if c == 5: # and _word[0] in _CTRL:
                c = _word.pop(0)
                if c not in _CTRL:
                    trns.append(f"<UNK>")
                else:
                    trns.append(_CTRL[c])
                    continue

            try:
                #trns.append(chars[c])
                trns.append(chars.get(c, f"<CTL {c}>"))
            except KeyError:
                raise ValueError(f"Undefined sequence {c}, next {_word[0]}\n{word}")
            #trns = trns.replace(b'\x05', b'\x01') # could actually be \x05\xff not sure

        return "".join(trns)

    return "".join([_CHARS.get(i, "?") for i in word])

def transcode(word):
    """
    Transcode ASCII characters to the FF6 integer code equivalents. Drops any value which does not have a character mapping.

    This is, roughly, the inverse of `translate`.

    :param word: (str) characters to convert
    :return: list of integers corresponding to characters
    """
    rmap = {v: k for k, v in _CHARS.items()}
    return [rmap[c] for c in word if c in rmap]

import argparse
argp = argparse.ArgumentParser()

argp.add_argument("-p", "--path-to-rom",
                  help="(required) Path to ROM file to dump scripts from.")
argp.add_argument("-S", "--no-suppress-empty", action='store_true',
                  help="Do not suppress empty messages.")
argp.add_argument("-l", "--long-form", action='store_true',
                  help="Emit bytestring along with translation")
_ALLOWED_LEVELS = ", ".join(logging._nameToLevel)
argp.add_argument("-L", "--log-level", default='WARN',
                  help=f"Set the log level. Default is WARN. Available choices are {_ALLOWED_LEVELS}.")

if __name__ == "__main__":
    args = argp.parse_args()
    # set logging
    log.setLevel(args.log_level.upper())

    src = args.path_to_rom
    if src is None:
        exit("Specify path to ROM with '-p'")
    if not os.path.exists(src):
        exit(f"Path {src} does not exist.")

    log.info(f"Reading {src}")
    with open(src, "rb") as fin:
        romfile = fin.read()
    batt_msgs = extract.extract_battle_msgs(romfile)

    for i, msg in batt_msgs.items():
        if len(msg) == 0 and not args.no_suppress_empty:
            continue
        tmsg = translate(msg, batt_msg=True)
        if not args.long_form:
            tmsg = tmsg.replace("\n", " / ")
        print(f"[{str(i).ljust(3)}] \"{tmsg}\"")
        if args.long_form:
            print("\t" + str(bytes(msg)))