import numpy
from . import flags

SYNTAX = {
    0xF0: (3, 0x100, "CHOOSE SPELL"),
    # Targetting technically only uses 1 byte, but the next is the attack
    0xF1: (1, ">", "TARGETTING"),
    0xF2: (3, "<>", "CHANGE FORMATION"),
    0xF3: (2, "\"", "DISPLAY MESSAGE"),
    0xF4: (3, "!", "USE COMMAND"),
    0xF5: (3, "~", "ALTER FORMATION"),
    0xF6: (3, "", "THROW / USE ITEM"),
    0xF7: (1, 0x107, "SPECIAL EVENT"),
    0xF8: (2, 0x108, "VAR MATH"),
    0xF9: (3, 0x109, "VAR MANIP"),
    0xFA: (3, 0x10A, "SPECIAL ACTION"),
    0xFB: (2, 0x10B, "MISC."),
    0xFC: (3, None, "CMD PRED"),
    0xFD: (None, None, "WAIT"),
    0xFE: (None, None, "END FC BLOCK"),
    0xFF: (None, None, "END BLOCK"),

    "_": (1, 0x10C, "DO SKILL"),
    "^": (None, None, "BEGIN SCRIPT"),
}

_CMD_REF = {}


class Cmd:
    def __init__(self, byteval=None, nargs=None, descr=""):
        self.byteval = byteval
        self.nargs = nargs
        self.descr = descr
        self._argument_types = []

        self.arg_shuffle_allowed = False

    def _iter_args(self, *args):
        arg_types = self._argument_types or [None] * self.nbytes
        for arg, _type in zip(args, arg_types):
            if isinstance(_type, (list, dict)):
                descr = _type[arg]
            elif _type is None:
                descr = None
            else:
                descr = _type(descr)
        yield arg, descr

    def expand(self, arg_g):
        """
        Expand the command into its randomized parameters with argument graph `arg_g`.

        :param arg_g: `networkx.DiGraph` a graph containing the relationships between the parameters; must include the command byte as well
        :return: a `list` of byte values corresponding to the command parameters
        """
        stack = []

        gptr = arg_g[self.byteval]
        while len(stack) < (self.nargs or 0):
            try:
                gptr = numpy.random.choice(list(gptr))
                stack.append(gptr)
            except ValueError:
                gptr = self.byteval

            gptr = arg_g[gptr]

        return stack

    def validate(self, script, ptr):
        return True

    def to_str(self):
        return f"[{hex(self.byteval)}] {self.descr}\n"

class EndBlock(Cmd):
    """
    The first EndBlock signifies the end of the "main" command block.
    The second EndBlock signifies the end of the counter / final attack block and the script itself.
    """
    def __init__(self):
        super().__init__(0xFF, None, descr="END BLOCK")

_CMD_REF[0xFF] = EndBlock

class EndPredBlock(Cmd):
    """
    Signifies the end of influence of a CmdPredicate.
    """
    def __init__(self):
        super().__init__(0xFE, None, descr="END FC BLOCK")

    def validate(self, script, ptr):
        # Ensure we actually have an FC block to end
        try:
            fci = script[:ptr][::-1].find(0xFC)
        except ValueError:
            return False
        fei = script[:ptr][::-1].find(0xFE) if 0xFE in script[:ptr] else -1
        ffi = script[:ptr][::-1].find(0xFF) if 0xFF in script[:ptr] else -1

        # We encountered an end block before the beginning of the
        # predicate
        # FIXME: This will get confused by "nothing"
        if fci > fei or fci > ffi:
            return False

        return super().validate(script, ptr)

_CMD_REF[0xFE] = EndPredBlock

class Wait(Cmd):
    """
    Signifies that the monster will do nothing this turn.
    """
    def __init__(self):
        super().__init__(0xFD, None, descr="WAIT")

_CMD_REF[0xFD] = Wait

class DoSkill(Cmd):
    """
    Unconditionally perform the specified skill.

    NOTE: this is not an actual byte-valued command. It is a placeholder so that
    the script parser does not confuse it for other commands or their parameters.
    """
    def __init__(self):
        super().__init__("_", 1, descr="DO SKILL")
        self._argument_types = [flags.SPELL_LIST]
        self.arg_shuffle_allowed = True

    def to_str(self, arg):
        return f"[] {arg}"

_CMD_REF["_"] = DoSkill

class ChooseSpell(Cmd):
    """
    Randomly selects a skill to perform from the next three bytes.
    """
    def __init__(self):
        super().__init__(0xF0, 3, descr="CHOOSE SPELL")
        self._argument_types = [flags.SPELL_LIST] * self.nargs
        self.arg_shuffle_allowed = True

    def to_str(self, *args):
        return super().to_str() + f"\t[+{self.nbytes}] " + " | ".join([flags.SPELL_LIST[s] for s in args])

_CMD_REF[0xF0] = ChooseSpell

class Targeting(Cmd):
    """
    The next attack will use the target specified by the byte after this.
    """
    def __init__(self):
        super().__init__(0xF1, 1, descr="TARGETING")
        self._argument_types = [flags.TARGET_LIST]
        self.arg_shuffle_allowed = True

    def validate(self, script, ptr):
        # Cannot have a "dangling" target
        if script[ptr + 2] in {0xFF, 0xFE}:
            return False
        return super().validate(script, ptr)

    def to_str(self, *args):
        return super().to_str() + f"\t[+{self.nbytes}] " + " | ".join([flags.TARGET_LIST.get(s, "<UNK>") for s in args])

_CMD_REF[0xF1] = Targeting

class ChangeFormation(Cmd):
    """
    Used to switch between formations.

    Parameters: [unknown = 0] [formation byte 1] [formation byte 2]

    From the scripting guide:
    The first bit of last byte determines if the monsters should get Max HP or not.
    If it's 1, then the monsters get max HP.
    If it's 0, then monsters retain HP and max HP from current formation.
    """
    def __init__(self):
        super().__init__(0xF2, 3, descr="CHANGE FORMATION")
        self._argument_types = [int, int]

    def validate(self, script, ptr):
        # will probably need to check that the formation being switched to is valid
        return super().validate(script, ptr)

    _HP_MASK = 1 << 15
    def to_str(self, *args):
        form = int.from_bytes(args[1:3], "little")
        with_hp = (form & self._HP_MASK) == self._HP_MASK
        form = ((form << 1) & 0xFFFF) >> 1
        with_hp = " WITH MAX HP" if with_hp else ""
        return super().to_str() + f"[{args[0]}] {hex(form)}" + with_hp

_CMD_REF[0xF2] = ChangeFormation

class DisplayMsg(Cmd):
    """
    Display a message indicated by the next two bytes.
    """
    def __init__(self):
        super().__init__(0xF2, 2, "DISPLAY MESSAGE")
        self._argument_types = [int, int]

_CMD_REF[0xF3] = DisplayMsg

class UseCommand(Cmd):
    """
    Execute a command chosen randomly from the next three bytes.

    NOTE: Not all commands work properly.
    """
    _VALID_COMMANDS = {f for f, s in flags.CMD_LIST.items()
                       if s.startswith("(") or s == "Nothing"}

    def __init__(self):
        super().__init__(0xF4, 3, "USE COMMAND")
        self._argument_types = [flags.CMD_LIST] * 3
        self.arg_shuffle_allowed = True

    def validate(self, script, ptr, strict=False):
        args = set(script[ptr+1:ptr+self.nargs+1])
        if strict and not args.issubset(self._VALID_COMMANDS):
            return False
        elif not args.issubset(flags.CMD_LIST):
            return False

        super().validate(script, ptr)

_CMD_REF[0xF4] = UseCommand

class AlterFormation(Cmd):
    """
    Alter the current formation.

    [animation byte] [hide/kill] [monster bits]

    From the scripting guide:
    If byte 2 is 0 then monsters are brought in that are currently hidden or killed at full max HP.
    If byte 2 is 1 then monsters are killed.
    If byte 2 is 2 then monsters are brought in at their current HP.
    If byte 2 is 3 then monsters are hidden and restored to full HP
    If byte 2 is 4 then monsters are hidden without restoring HP
    """

    def __init__(self):
        super().__init__(0xF5, 3, "ALTER FORMATION")
        self._argument_types = [int, int, int]

    def to_str(self, *args):
        status = {
            0: "SHOWN AND KILLED(?)",
            1: "KILLED",
            2: "SHOWN",
            3: "HIDDEN AT MAX HP",
            4: "HIDDEN"
        }.get(args[1], "???")
        return super().to_str() + f"{hex(args[0])} {status} {bin(args[2])}"

_CMD_REF[0xF5] = AlterFormation

class ThrowUseItem(Cmd):
    """
    Throw or use (first byte) randomly selected item from next two bytes

    [0 = use | 1 = throw] [item1] [item2]
    """
    def __init__(self):
        super().__init__(0xF6, 3, "THROW / USE ITEM")
        self._argument_types = [int] + [flags.ITEM_LIST] * 2
        self.arg_shuffle_allowed = True

    def to_str(self, *args):
        args = [f(a) for f, a in zip(self._argument_types, args)]
        toggle = 'use' if args[0] == 0 else 'throw'
        return super().to_str() + f"{toggle} " + " | ".join(args[1:])

_CMD_REF[0xF6] = ThrowUseItem

class SpecialEvent(Cmd):
    """
    Trigger a special in-battle event specified by next byte.

    [event]
    """
    # FIXME: need event list
    def __init__(self):
        super().__init__(0xF7, 1, "SPECIAL EVENT")
        self._argument_types = [int]
        self.arg_shuffle_allowed = True

    def to_str(self, arg):
        return super().to_str() + hex(arg)

_CMD_REF[0xF7] = SpecialEvent

class VarMath(Cmd):
    """
    Perform some math on the specified variable.

    [var id] [operation & value]

    From the scripting guide:
    The second byte determines the operation to use, and the operand. Bits 6 and 7 determine the operation:

    Value	Operation
    00	    Set variable
    01	    Set variable
    10	    Add to variable
    11	    Subtract from variable
    """
    def __init__(self):
        super().__init__(0xF8, 2, "VAR MATH")
        self._argument_types = [int, int, int]

    def _oper(self, val):
        # FIXME: do we have this reversed?
        return {
            0: "SET",
            1: "SET",
            2: "ADD",
            3: "SUB"
        }.get((val >> 6) & 0x3, "???")

    def validate(self, script, ptr):
        # Need to check that variables are present and accounted for
        return super().validate(script, ptr)

    def to_str(self, *args):
        oper = self._oper(args[1])
        val = args[1] & 0x3F
        return super().to_str() + f"{hex(args[0])} {oper} {val}"

_CMD_REF[0xF8] = VarMath

class VarManip(Cmd):
    """
    Perform bitwise mainpulation on the specified variable.

    [operation] [var id] [bit]

    From the scripting guide:
    Byte 1 is the operation:
    Value	Operation
    0	Toggle bit
    1	Set bit
    2	Clear bit
    """
    def __init__(self):
        super().__init__(0xF9, 3, "VAR MANIP")
        self._argument_types = [int, int, bin]

    def _oper(self, value):
        return {
            0: "TOGGLE",
            1: "SET",
            2: "CLEAR"
        }.get(value, "???")

    def validate(self, script, ptr):
        # Need to check that variables are present and accounted for
        return super().validate(script, ptr)

    def to_str(self, *args):
        oper = self._oper(args[0])
        return super().to_str() + f"{oper} {hex(args[1])} {bin(args[2])}"

_CMD_REF[0xF9] = VarManip

class SpecAct(Cmd):
    """
    Animation effects, specified by next byte, targeting the byte thereafter.

    [animation id] [target] [unk.]
    """
    def __init__(self):
        super().__init__(0xFB, 3, "SPECIAL ACTION")
        self._argument_types = [flags.ANIMATIONS, flags.TARGET_LIST, None]

    def to_str(self, *args):
        anim = flags.ANIMATIONS[args[0]]
        targ = flags.TARGET_LIST[args[1]]
        return super().to_str() + f"{anim} {targ}"

_CMD_REF[0xFA] = SpecAct

class Misc(Cmd):
    """
    Miscellaneous effects, specified by next byte, targeting the byte thereafter.

    [effect] [target]
    """
    def __init__(self):
        super().__init__(0xFB, 2, "MISC.")

    def to_str(self, *args):
        effect = flags.MISC[args[0]]
        targ = flags.TARGET_LIST[args[1]]
        return self.to_str() + f"{effect} {targ}"

_CMD_REF[0xFB] = Misc

class CmdPred(Cmd):
    """
    Predicate all actions on the evaluated truth value of this command until the block is ended.

    [modifier type] [param1] [param2]
    NOTE: This can be ended by 0xFE or OxFF.
    """
    def __init__(self):
        super().__init__(0xFC, 3, "CMD PRED")
        self._argument_types = [flags.FC_MODIFIERS, int, int]

    def validate(self, script, ptr):
        # This one is probably the most complicated one we'll have to check
        # Need to make sure all targets / variables are represented properly
        return super().validate(script, ptr)

    def to_str(self, *args):
        mod = flags.FC_MODIFIERS[args[0]]
        return super().to_str() + f"\t{mod} " + " ".join(map(hex, args[1:3]))

_CMD_REF[0xFC] = CmdPred