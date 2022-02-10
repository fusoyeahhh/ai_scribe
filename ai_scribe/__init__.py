import logging
log = logging.getLogger("ai_scribe")

_BOSS_DIFFICULTY_SCALING = 1.5
_MIN_BOSS_DIFFICULTY = 0.5

_NAME_ALIASES = {
    # BC often renames this
    "L.255Magic": "MagiMaster",

    # These enemies do not have names in the ROM
    366: "Terra In Flashback",
    "": "Terra In Flashback",
    367: "Kefka at Imperial Camp",
    "2": "Kefka at Imperial Camp",
    368: "Cyan at Imperial Camp",
    "3": "Cyan at Imperial Camp",
    370: "Gau on Veldt",
    "4": "Gau on Veldt",
    371: "Kefka at Thamasa",
    "5": "Kefka at Thamasa",
    372: "Kefka on Bridge",
    "6": "Kefka on Bridge",
    375: "Dummy?",
    "7": "Dummy?",
    376: "Dummy??",
    "8": "Dummy??",
    378: "Ifrit Clone",
    "9": "Ifrit Clone",
    379: "Kefka on the Bridge (scene mgr.)",
    "10": "Kefka on the Bridge (scene mgr.)",
    380: "Dummy???",
    "11": "Dummy???",
    382: "Dummy????",
    "12": "Dummy????",
    383: "Dummy?????",
    "13": "Dummy?????",
    282: "Final Kefka (scene mgr.)??",
    "Kefka": "Final Kefka (scene mgr.)??",
    298: "Final Kefka",
    "Kefka2": "Final Kefka",
    330: "Kefka at Narshe",
    "Kefka3": "Kefka at Narshe",
    273: "Guardian at Vector",
    "Guardian": "Guardian at Vector",
    274: "Guardian (KT boss)",
    "Guardian2": "Guardian (KT boss)",
    269: "Left Crane",
    "Crane": "Left Crane",
    270: "Right Crane",
    "Crane2": "Right Crane",
    271: "Umaro (dummied)",
    "Umaro": "Umaro (dummied)",
    272: "Umaro (Narshe WoR boss)",
    "Umaro2": "Umaro (Narshe WoR boss)",
    276: "Tritoch (Narshe Cave)",
    "Tritoch": "Tritoch (Narshe Cave)",
    277: "Tritoch (Narshe Cliff)",
    "Tritoch2": "Tritoch (Narshe Cliff)",
    324: "Tritoch (Narshe Boss)",
    "Tritoch3": "Tritoch (Narshe Boss)",
    127: "SrBehemoth (second)",
    "SrBehemoth": "SrBehemoth (second)",
    281: "SrBehemoth (first)",
    "SrBehemoth2": "SrBehemoth (first)",
    300: "Ultros (Lete River)",
    "Ultros": "Ultros (Lete River)",
    301: "Ultros (Opera House)",
    "Ultros2": "Ultros (Opera House)",
    302: "Ultros (Esper Mountain)",
    "Ultros3": "Ultros (Esper Mountain)",
    360: "Ultros (Airship)",
    "Ultros4": "Ultros (Airship)",
    64: "Chupon (Coloseum)",
    "Chupon": "Chupon (Coloseum)",
    303: "Chupon (Airship)",
    "Chupon2": "Chupon (Airship)",
    305: "Siegfried (Ghost Train)",
    "Siegfried2": "Siegfried (Ghost Train)",
    328: "Chadarnook (Demon)",
    "Chadarnook2": "Chadarnook (Demon)",
    286: "Chadarnook (Goddess)",
    "Chadarnook": "Chadarnook (Goddess)",
    #377: "Solider (Terra Flashback)",
    "Solider2": "Solider (Terra Flashback)",
}

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

def verify_rom(outfname, export, names):
    from .extract import extract

    new_scripts, new_names, _ = extract(outfname, return_names=True)
    for n, scr in new_scripts.items():
        same = scr._bytes == export[n]._bytes
        name = names[n]

        # Check for same to within padding
        end = min(len(export[n]._bytes), len(scr._bytes))
        close = (set(scr._bytes[end:]) == set(b'\xff')) \
                | (set(export[n]._bytes[end:]) == set(b'\xff'))
        close &= scr._bytes[:end] == scr._bytes[:end]

        if scr.ptr == 0xF8700 and not same:
            log.debug(f"TRUNCATED: {n} ({name})")
            log.debug(f"{hex(scr.ptr)} <-> {hex(export[n].ptr or 0)}")
            continue
        elif close:
            log.debug(f"BUFFERED: {n} ({name})")
            log.debug(f"{hex(scr.ptr)} <-> {hex(export[n].ptr or 0)}")
            log.debug(tableau_scripts(scr.translate(), export[n].translate()))
            continue
        elif not same:
            # print(n, scr._bytes, export[n]._bytes)
            log.warning(f"DIFFERENCE: {n} ({name})")
            log.warning(f"{hex(scr.ptr)} <-> {hex(export[n].ptr or 0)}")
            log.warning(tableau_scripts(scr.translate(), export[n].translate()))
        assert scr._bytes == export[n]._bytes, n