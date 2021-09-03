# These enemies do not have names in the ROM
_NAME_ALIASES = {
    "": "Terra In Flashback",
    #"2": "",
    "3": "Cyan at Imperial Camp",
    #"4": "",
    #"5": "",
    #"6": "",
    "7": "Dummy?",
    "8": "Dummy??",
    "9": "Ifrit Clone",
    #"10": "",
    "11": "Dummy???",
    "12": "Dummy????",
    #"13": "",
}

def tableau_scripts(s1, s2):
    s1 = s1.replace("\t", "  ").split("\n")
    s2 = s2.replace("\t", "  ").split("\n")
    mlen1 = max([len(l) for l in s1])
    mlen2 = max([len(l) for l in s2])
    #mlen = max(len(s1), len(s2))
    ldiff = abs(len(s1) - len(s2))

    fmt_str = "\n".join([_s1.rstrip().ljust(mlen1) + " | " + _s2.rstrip().ljust(mlen2)
                                for _s1, _s2 in zip((s1 + ["\n" * ldiff]), (s2 + ["\n" * ldiff]))])
    return fmt_str
