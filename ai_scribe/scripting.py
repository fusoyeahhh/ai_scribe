from . import flags
from .syntax import SYNTAX

# Upper case
_CHARS = {128 + i: chr(j) for i, j in enumerate(range(65, 65 + 26))}
# Lower case
_CHARS.update({154 + i: chr(j) for i, j in enumerate(range(97, 97 + 26))})
# Numbers
_CHARS.update({180 + i: chr(j) for i, j in enumerate(range(48, 48 + 10))})
# FIXME: Will probably need symbols at some point
_CHARS[191] = "?"
_CHARS[197] = "."
_CHARS[255] = ""

def translate(script):
    script = [*script].copy()
    script.append(-0x1)
    s = ""
    while True:
        v = script.pop(0)
        if v == -0x1:
            break
        try:
            v = int(v)
        except ValueError:
            pass

        if v not in SYNTAX:
            #print(f"[] {flags.SPELL_LIST[v]}")
            s += f"[] {flags.SPELL_LIST[v]}\n"
            continue

        nbytes, placeholder, descr = SYNTAX[v]
        ext = f"+{nbytes}" if nbytes is not None else ""
        s += f"[{hex(v)}{ext}] {descr}\n"

        if v == 0xFC:
            mod1, mod2, mod3 = script[:3]
            script = script[3:]

            mod1 = flags.FC_MODIFIERS.get(mod1, hex(mod1))
            #print(f"\t{mod1} {hex(mod2)} {hex(mod3)}")
            s += f"\t{mod1} {hex(mod2)} {hex(mod3)}\n"
            continue

        if placeholder is not None:
            if v == 0xF0:
                v = " | ".join([flags.SPELL_LIST[s] for s in script[:nbytes]])
            elif v == 0xF1:
                v = " | ".join([flags.TARGET_LIST.get(s, "<UNK>") for s in script[:nbytes]])
            elif v == 0xF6:
                v = f"{'use' if script[0] == 0 else 'throw'} {flags.ITEM_LIST[script[1]]} {flags.ITEM_LIST[script[2]]}"
            elif v == 0xF4:
                v = " | ".join([flags.CMD_LIST.get(s, "{ILLEGAL}") for s in script[:nbytes]])
            elif v == 0xFA:
                v = f"{flags.ANIMATIONS[script[0]]} {hex(script[1])} {hex(script[2])}"
            elif v == 0xFC:
                v = f"{flags.FC_MODIFIERS.get(script[0], script[0])} {hex(script[1])} {hex(script[2])}"
            elif v == 0xFB:
                v = f"{flags.MISC.get(script[0], hex(script[0]))} {hex(script[1])}"
            else:
                v = " ".join(map(hex, script[:nbytes]))
            s += f"\t{v}\n"
            script = script[nbytes:]

    return s

fire_once = [*b'\xfc\x15\x03\x00\xf9\x00\x03\x00']
def add_one_time_trigger(script, trigger):
    return fire_once + trigger + script

class Script:
    def __init__(self, content=b"", name=None):
        self._bytes = content
        self.name = name

    PTR_NAME_OFFSET = 0xFC050 - 0xF8700
    @classmethod
    def from_rom(cls, ptr, plen, name, romfile):
        s = e = ptr
        e += plen
        return Script(romfile[s:e], name)

        return script

    def __len__(self):
        return len(self._bytes)

    def __bytes__(self):
        return self._bytes

    def to_graph(self):
        # FIXME: invert the dependency here?
        from command_graph import CommandGraph
        g = CommandGraph.from_scripts({self.name: self._bytes})
        return g

    def to_script_objs(self):
        pass

    #def __repr__(self):
    def translate(self):
        return translate(self._bytes)