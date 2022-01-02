from . import flags
from . import syntax
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
_CHARS[254] = " "
_CHARS[196] = "-"

def translate(script, memblk=False, allow_partial=False):
    script = [*script].copy()
    script.append(-0x1)
    s = ""

    if memblk:
        for i, b in enumerate(script):
            if i % 16 == 0:
                s += "\n" + hex(i).rjust(6) + " "
            s += hex(b).rjust(4) + " "
        s += "\n"

    while True:
        try:
            v = script.pop(0)
        except Exception as e:
            if allow_partial:
                print(e)
                return s
            raise e
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
                v = " | ".join([flags.TARGET_LIST.get(s, f"<UNK> {hex(s)}") for s in script[:nbytes]])
            elif v == 0xF6:
                v = f"{'use' if script[0] == 0 else 'throw'} {flags.ITEM_LIST[script[1]]} {flags.ITEM_LIST[script[2]]}"
            elif v == 0xF4:
                v = " | ".join([flags.CMD_LIST.get(s, "{ILLEGAL}") for s in script[:nbytes]])
            elif v == 0xF7:
                v = flags.SPECIAL_EVENTS.get(script[0], f"{{UNKNOWN, {hex(script[0])}}}")
            elif v == 0xFA:
                try:
                    v = f"{flags.ANIMATIONS[script[0]]} {hex(script[1])} {hex(script[2])}"
                except IndexError:
                    v = f"UNPARSEABLE {hex(script[0])}"
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
    def __init__(self, content=b"", name=None, ptr=None):
        self.ptr = ptr
        self._bytes = content
        self.name = name

    @classmethod
    def from_rom(cls, ptr, plen, name, romfile):
        s = e = ptr
        e += plen
        return Script(romfile[s:e], name, ptr)

    def __len__(self):
        return len(self._bytes)

    def __bytes__(self):
        return self._bytes

    def __repr__(self):
        if self._bytes is None:
            return "<Script: {self.name}, Empty>"
        return f"<Script: {self.name}, {hex(self.ptr or 0)}+{len(self._bytes)}>"

    def to_graph(self):
        # FIXME: invert the dependency here?
        from command_graph import CommandGraph
        g = CommandGraph.from_scripts({self.name: self._bytes})
        return g

    def to_script_objs(self):
        pass

    @classmethod
    def validate(cls, script, allow_empty_fc=False):
        if not script[-1] == 0xFF:
            assert script.endswith(b'\xFF'), translate(script, memblk=True, allow_partial=True)
            return False

        # This checks for less than two 0xFF and that the script isn't empty
        # NOTE: This will be confused by 0xFF ("nothing") in skill based commands
        try:
            ffi2 = script.index(0xFF, script.index(0xFF) + 1)
        except ValueError:
            raise ValueError(f"Script has less than two 0xFF\n" +
                             translate(script, memblk=True, allow_partial=True))
            return False

        # This checks that the script isn't "empty"
        #if ffi2 <= 1:
            #return False

        # Check for empty FC blocks
        for i in range(len(script) - 5):
            if not allow_empty_fc and script[i] == 0xFC and script[i + 4] in {0xFE, 0XFF}:
                raise ValueError(f"Script hase empty FC block\n" +
                                 translate(script, memblk=True, allow_partial=True))
                return False

        # Translating can reveal parsing errors
        try:
            translate(script)
        except:
            #print(translate(script, memblk=True, allow_partial=True))
            raise ValueError("Couldn't translate script.")
        return True

    #def __repr__(self):
    def translate(self, **kwargs):
        cpy = self._bytes

        trans = ""
        while len(cpy) > 0:
            if syntax.Cmd._CMD_REG.get(cpy[0], None) is None:
                trans += "[] " + syntax.DoSkill.format_args(cpy.pop(0)) + "\n"
                continue

            cmd = syntax.Cmd._CMD_REG.get(cpy.pop(0), None) or cmd
            nbytes, descr = cmd._NARGS, cmd._DESCR

            args, cpy = cpy[:nbytes], cpy[nbytes:]
            fmtargs = cmd.format_args(*args)

            bval = cmd._BYTEVAL if cmd._BYTEVAL == "_" else hex(cmd._BYTEVAL)
            ext = f"+{nbytes}" if nbytes is not None or nbytes != 0 else ""
            args = "".join([f"{arg:02x}" for arg in args])
            trans += f"[{bval}{ext}:{str(args)}] {descr}\n"
            if fmtargs != "":
                trans += "\t" + fmtargs + "\n"

        return trans

    #def translate(self, **kwargs):
        #return translate(self._bytes, **kwargs)

    def entropy(self, rhs=None):
        from collections import Counter
        import math

        p1 = Counter()
        for v in self._bytes:
            p1[v] += 1

        if rhs is not None:
            p2 = Counter()
            for v in self._bytes:
                p2[v] += 1
            return sum([math.log2(n / m) for n, m in zip(p1, p2)])

        return sum([math.log2(n) for n in p1])

# rules
_RULES = {}

class Rule:
    # put in flags
    ALL_SKILLS = set(range(256))
    # FIXME: fill out
    PLAYER_TARGETS = {k for k, v in flags.TARGET_LIST.items() if v not in set()}
    # put in syntax
    EXCEPT_ATTACKS = {"_"} | (set(range(0xF1, 0xFF)) - {0xF0})
    RULESETS = {
        # disallow self targeting with harmful effects
        "no_self_target":
            [((0xF1, {0x36}), (0xF0, ...)),
             ((0xF1, {0x36}), ("_",  ...))],

        # disallow player healing
        "no_player_heal":
            [((0xF1, PLAYER_TARGETS), (0xF0, flags.CURATIVES)),
             ((0xF1, PLAYER_TARGETS), ("_",  flags.CURATIVES))],
        # FIXME this is a different rule
        #((0xF6, PLAYER_TARGETS), ("_",  flags.CURATIVES))],

        # Example: disallow empty FC block
        "no_empty_fc":
            [((0xFC, ...), (0xFF, None)),
             ((0xFC, ...), (0xFE, None))],

        # Example: do nothing connections
        "no_do_nothing":
            [((0xF1, ...), (c, ...)) for c in EXCEPT_ATTACKS],

        # The following are less useful as rules and
        # could be in validation step
        # Example: disallow a specific spell (Fire)
        "no_fire":
            [((None, None), (0xF0, {0x0})),
             ((None, None), ("_",  {0x0}))],

        # Example: allow only certain items to be used
        "standard_items":
            [((None, None), (0xF6, {...}))],
    }

    @classmethod
    def get_nth_token_from_end(cls, script, n=1, with_args=False):
        tidx = len(script)
        while n > 0:
            tidx -= 1
            if not isinstance(script[tidx], (int, bytes)):
                n -= 1

        if with_args:
            arglen = tidx + (script[tidx]._NARGS or 0) + 1
            return script[tidx], script[tidx+1:arglen]
        return script[tidx]

    # Does the rule apply and is triggered?
    def __call__(self, script, **ctx):
        pass

    def suggest(self, script, **ctx):
        pass
    
class NoEmptyCondBlock(Rule):
    def __call__(self, script, **ctx):
        # get last token
        try:
            tok = self.get_nth_token_from_end(script, n=1)
        except IndexError:
            return False

        return isinstance(tok, syntax.EndPredBlock) \
                and ctx["nfc"] == 0
_RULES["no_empty_cond_block"] = NoEmptyCondBlock

class NoNestedCondBlock(Rule):
    def __call__(self, script, **ctx):
        # get last two tokens
        try:
            rhs, rargs = self.get_nth_token_from_end(script, n=1, with_args=True)
            lhs, largs = self.get_nth_token_from_end(script, n=2, with_args=True)
        except IndexError:
            return False

        if ctx["nfc"] == 0:
            return False
        if ctx["nfc"] >= 1 and rhs is syntax.CmdPred:
            return True
        return False
_RULES["no_nested_cond_block"] = NoNestedCondBlock

class CurativesOnlyTargetAllies(Rule):
    VALID_TARGETABLE = (syntax.DoSkill, syntax.ChooseSpell,
                        syntax.ThrowUseItem, syntax.UseCommand)

    def __call__(self, script, **ctx):
        # get last two tokens
        try:
            rhs, rargs = self.get_nth_token_from_end(script, n=1, with_args=True)
            lhs, largs = self.get_nth_token_from_end(script, n=2, with_args=True)
        except IndexError:
            return False

        # FIXME: only works for DoSkill
        if isinstance(lhs, syntax.Targeting) \
           and isinstance(rhs, self.VALID_TARGETABLE):
            return largs[0] in flags.SELF_TARGETS \
                   and rargs[0] in flags.CURATIVES
        return False
_RULES["curatives_only_target_self"] = CurativesOnlyTargetAllies

class BanSkill(Rule):
    def __init__(self, banned_skills):
        super().__init__()
        self.banned_skills = banned_skills

    def __call__(self, script, **ctx):
        # get last token
        tok, skill = self.get_nth_token_from_end(script, n=1, with_args=True)

        return isinstance(tok, syntax.DoSkill) \
                and set(skill) & self.banned_skills
_RULES["ban_skill"] = BanSkill
