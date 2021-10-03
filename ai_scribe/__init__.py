# These enemies do not have names in the ROM
_NAME_ALIASES = {
    "": "Terra In Flashback",
    "2": "Kefka at Imperial Camp",
    "3": "Cyan at Imperial Camp",
    "4": "Gau on Veldt",
    "5": "Kefka at Thamasa",
    "6": "Kefka on Bridge",
    "7": "Dummy?",
    "8": "Dummy??",
    "9": "Ifrit Clone",
    "10": "Kefka on the Bridge (scene mgr.)",
    "11": "Dummy???",
    "12": "Dummy????",
    "13": "Dummy?????",
    "Kefka": "Final Kefka (scene mgr.)??",
    "Kefka2": "Final Kefka",
    "Kefka3": "Kefka at Narshe",
    "Guardian": "Guardian at Vector",
    "Guardian2": "Guardian (KT boss)",
    #"Crane": "Left Crane",
    #"Crane2": "Right Crane",
    "Umaro": "Umaro (dummied)",
    "Umaro2": "Umaro (Narshe WoR boss)",
    "Tritoch": "Tritoch (Narshe Cave)",
    "Tritoch2": "Tritoch (Narshe Cliff)",
    "Tritoch3": "Tritoch (Narshe Boss)",
    "SrBehemoth": "SrBehemoth (second)",
    "SrBehemoth2": "SrBehemoth (first)",
    "Ultros": "Ultros (Lete River)",
    "Ultros2": "Ultros (Opera House)",
    "Ultros3": "Ultros (Esper Mountain)",
    "Ultros4": "Ultros (Airship)",
    "Chupon": "Chupon (Coloseum)",
    "Chupon2": "Chupon (Airship)",
    "Siegfried2": "Siegfried (Ghost Train)",
    "Chadarnook2": "Chadarnook (Demon)",
    "Chadarnook": "Chadarnook (Goddess)",
    "Solider2": "Solider (Terra Flashback)",
}

ENEMY_DATA_OFFSET = 0xF0000
ENEMY_DATA_SIZE = 0x20
ENEMY_DATA_BLOCKS = 0x180
ENEMY_MP_REL_OFFSET = 0x0A
def give_base_mp(romfile):

    ptr = ENEMY_DATA_OFFSET + ENEMY_MP_REL_OFFSET
    for i in range(ENEMY_DATA_BLOCKS):
        mp = max(20, int.from_bytes(romfile[ptr:ptr + 2], "little"))
        romfile = romfile[:ptr] + mp.to_bytes(2, "little") + romfile[ptr + 2:]
        ptr += ENEMY_DATA_SIZE

    return romfile

def tableau_scripts(s1, s2):
    s1 = s1.replace("\t", "  ").split("\n")
    s2 = s2.replace("\t", "  ").split("\n")
    mlen1 = max([len(l) for l in s1])
    mlen2 = max([len(l) for l in s2])
    #mlen = max(len(s1), len(s2))
    ldiff = abs(len(s1) - len(s2))

    fmt_str = "\n".join([_s1.rstrip().ljust(mlen1) + " | " + _s2.rstrip().ljust(mlen2)
                                for _s1, _s2 in zip((s1 + ["\n"] * ldiff), (s2 + ["\n"] * ldiff))])
    return fmt_str
