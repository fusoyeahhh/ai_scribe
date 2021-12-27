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

# FIXME: merge with SYNTAX
_CMD_REF = {}

class Cmd:
    @classmethod
    def get_by_byteval(cls, byteval):
        return _CMD_REF[byteval]

    def __init__(self, byteval, nargs, descr=""):
        self.byteval = byteval
        self.nargs = nargs
        self.descr = descr

    def __call__(self, arg_g, *args):
        # could also do rules here
        return f"[{hex(self.byteval)}+{self.nargs}] {self.descr}\n" + self.format_args(*self.expand(arg_g))

    def parse_args(self, script):
        return [(arg, None) for arg in script[:self.nargs]]

    def format_args(self, *args, joiner=" | "):
        return joiner.join([*map(str, args)])

    def to_str(self):
        return f"[{hex(self.byteval)}] {self.descr}\n"

    def expand(self, arg_g, virtual=False):
        """
        Expand the command into its randomized parameters with argument graph `arg_g`.

        :param arg_g: `networkx.DiGraph` a graph containing the relationships between the parameters; must include the command byte as well
        :param virtual: Command is not actually in syntax, so do not prepend it to result
        :return: a `list` of byte values corresponding to the command parameters
        """
        # We may not need the syntax marker
        stack = [] if virtual else [self.byteval]

        gptr = arg_g[self.byteval]
        while len(stack) < (self.nargs or 0):
            try:
                gptr = numpy.random.choice(list(gptr))
                stack.append(gptr)
            except ValueError:
                gptr = self.byteval

            gptr = arg_g[gptr]

        return stack

class ChooseSpell(Cmd):
    """
    Randomly selects a skill to perform from the next three bytes.
    """
    _BYTEVAL = 0xF0
    _ALLOWED_ARGS = set(flags.SPELL_LIST)
    _NOTHING = 0xFF
    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "CHOOSE SPELL")

    def __call__(self, *args):
        # implement the actual command function with given args
        pass

    def parse_args(self, script):
        return [(arg, flags.SPELL_LIST[arg]) for arg in script[:self.nargs]]

    def expand(self, arg_g):
        arg = super().expand(arg_g)
        if any(arg not in self._ALLOWED_ARGS for arg in arg[1:]):
            raise
        return arg

_CMD_REF[ChooseSpell._BYTEVAL] = ChooseSpell

class DoSkill(Cmd):
    """
    Unconditionally perform the specified skill.

    NOTE: this is not an actual byte-valued command. It is a placeholder so that
    the script parser does not confuse it for other commands or their parameters.
    """
    _BYTEVAL = "_"
    _ALLOWED_ARGS = ChooseSpell._ALLOWED_ARGS - set(range(0xF0, 0x100))
    def __init__(self):
        super().__init__(self._BYTEVAL, 1, descr="DO SKILL")

    def expand(self, arg_g):
        super().format_args(arg_g, virtual=True)

    def format_args(self, *args):
        return flags.SPELL_LIST[args[0]]

_CMD_REF[DoSkill._BYTEVAL] = DoSkill

class Targeting(Cmd):
    """
    The next attack will use the target specified by the byte after this.
    """
    _BYTEVAL = 0xF1
    _ALLOWED_ARGS = flags.TARGET_LIST
    def __init__(self):
        super().__init__(self._BYTEVAL, 1, "TARGETTING")

_CMD_REF[Targeting._BYTEVAL] = Targeting

class ChangeFormation(Cmd):
    """
    Used to switch between formations.

    Parameters: [unknown = 0] [formation byte 1] [formation byte 2]

    From the scripting guide:
    The first bit of last byte determines if the monsters should get Max HP or not.
    If it's 1, then the monsters get max HP.
    If it's 0, then monsters retain HP and max HP from current formation.
    """
    _BYTEVAL = 0xF2
    # FIXME: how many allowed formations?
    _ALLOWED_ARGS = set(range(1024))
    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "CHANGE FORMATION")

    _HP_MASK = 1 << 15
    def format_args(self, *args):
        form = int.from_bytes(args[1:3], "little")
        with_hp = (form & self._HP_MASK) == self._HP_MASK
        form = ((form << 1) & 0xFFFF) >> 1
        with_hp = " WITH MAX HP" if with_hp else ""
        return hex(form) + with_hp

    # TODO: argument checking

_CMD_REF[ChangeFormation._BYTEVAL] = ChangeFormation

class DisplayMsg(Cmd):
    """
    Display a message indicated by the next two bytes.
    """
    _BYTEVAL = 0xF3
    # FIXME: get from module
    _ALLOWED_ARGS = set(range(256))
    def __init__(self):
        super().__init__(self._BYTEVAL, 2, "DISPLAY MESSAGE")

    def format_args(self, *args, msg_dict={}):
        form = int.from_bytes(args[1:2], "little")
        if form in msg_dict:
            return f"{hex(form)} = \"{msg_dict[form]}\""
        return hex(form)

_CMD_REF[DisplayMsg._BYTEVAL] = DisplayMsg

class UseCommand(Cmd):
    """
    Execute a command chosen randomly from the next three bytes.

    NOTE: Not all commands work properly.
    """
    _BYTEVAL = 0xF4
    _ALLOWED_ARGS = flags.CMD_LIST
    _VALID_COMMANDS = {f for f, s in flags.CMD_LIST.items()
                       if s.startswith("(") or s == "Nothing"}
    def __init__(self):
        super().__init__(self._BYTEVAL, 2, "DISPLAY MESSAGE")

_CMD_REF[UseCommand._BYTEVAL] = UseCommand

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
    _BYTEVAL = 0xF5
    _ALLOWED_ARGS = ...

    _STATUS = {
        0: "SHOWN AND KILLED(?)",
        1: "KILLED",
        2: "SHOWN",
        3: "HIDDEN AT MAX HP",
        4: "HIDDEN"
    }
    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "ALTER FORMATION")

    def format_args(self, *args):
        status = self._STATUS.get(args[1], "???")
        return f"{status} {bin(args[2])}"

_CMD_REF[AlterFormation._BYTEVAL] = AlterFormation

class ThrowUseItem(Cmd):
    """
    Throw or use (first byte) randomly selected item from next two bytes

    [0 = use | 1 = throw] [item1] [item2]
    """
    _BYTEVAL = 0xF6
    _ALLOWED_ARGS = flags.ITEM_LIST

    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "THROW / USE ITEM")

    def format_args(self, *args):
        args = [flags.ITEM_LIST[i] for i in args]
        toggle = 'use' if args[0] == 0 else 'throw'
        return f"{toggle} " + super.format_args(*args)

_CMD_REF[ThrowUseItem._BYTEVAL] = ThrowUseItem

class SpecialEvent(Cmd):
    """
    Trigger a special in-battle event specified by next byte.

    [event]
    """
    _BYTEVAL = 0xF7
    # FIXME: need event list
    _ALLOWED_ARGS = set(flags.SPECIAL_EVENTS)

    def __init__(self):
        super().__init__(self._BYTEVAL, 1, "SPECIAL EVENT")

    def format_args(self, *args):
        if args[0] in flags.SPECIAL_EVENTS:
            return f"{hex(args[0])} " + flags.SPECIAL_EVENTS[args[0]]
        return f"{hex(args[0])}"

_CMD_REF[SpecialEvent._BYTEVAL] = SpecialEvent

class VariableBase(Cmd):
    __VARIABLE_CONTEXT = set()

    def reset(self):
        self.__VARIABLE_CONTEXT = set()

    def get_random_var(self):
        pass

    def register_var(self):
        pass

class VarMath(VariableBase):
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
    _BYTEVAL = 0xF8
    _VALID_OPERS = {
        0: "SET",
        1: "SET",
        2: "ADD",
        3: "SUB"
    }

    @classmethod
    def _oper(cls, val):
        # FIXME: do we have this reversed?
        return cls._VALID_OPERS.get((val >> 6) & 0x3, "???")

    def __init__(self):
        super().__init__(self._BYTEVAL, 2, "VAR MATH")

    def format_args(self, *args):
        oper = self._oper(args[1])
        val = args[1] & 0x3F
        return f"{oper} {val}"

_CMD_REF[VarMath._BYTEVAL] = VarMath

class VarManip(VariableBase):
    """
    Perform bitwise mainpulation on the specified variable.

    [operation] [var id] [bit]

    From the scripting guide:
    Byte 1 is the operation:
    Value	Operation
    0	    Toggle bit
    1	    Set bit
    2	    Clear bit
    """
    _BYTEVAL = 0xF9
    _VALID_OPER = {
        0: "TOGGLE",
        1: "SET",
        2: "CLEAR"
    }

    @classmethod
    def _oper(cls, value):
        return cls._VALID_OPER.get(value, "???")

    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "VAR MANUP")

_CMD_REF[VarManip._BYTEVAL] = VarManip

class SpecAct(Cmd):
    """
    Animation effects, specified by next byte, targeting the byte thereafter.

    [animation id] [target] [unk.]
    """
    _BYTEVAL = 0xFA
    _VALID_ANIM = set(flags.ANIMATIONS)
    _VALID_TARGETS = set(flags.TARGET_LIST)
    _ALLOWED_ARGS = ...
    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "SPECIAL ACTION")

    def format_args(self, *args):
        return f"{flags.ANIMATIONS[args[0]]} {flags.TARGET_LIST[args[1]]}"

_CMD_REF[SpecAct._BYTEVAL] = SpecAct

class Misc(Cmd):
    """
    Miscellaneous effects, specified by next byte, targeting the byte thereafter.

    [effect] [target]
    """
    _BYTEVAL = 0xFB
    _VALID_MISC = set(flags.MISC)
    _VALID_TARGETS = set(flags.TARGET_LIST)
    _ALLOWED_ARGS = ...
    def __init__(self):
        super().__init__(self._BYTEVAL, 2, "MISC.")

    def format_args(self, *args):
        return f"{flags.MISC[args[0]]} {flags.TARGET_LIST[args[1]]}"

_CMD_REF[Misc._BYTEVAL] = Misc

class CmdPred(VariableBase):
    """
    Predicate all actions on the evaluated truth value of this command until the block is ended.

    [modifier type] [param1] [param2]
    NOTE: This can be ended by 0xFE or OxFF.
    """
    _BYTEVAL = 0xFC
    _VALID_MODS = flags.FC_MODIFIERS
    _ALLOWED_ARGS = ...
    def __init__(self):
        super().__init__(self._BYTEVAL, 3, "CMD PRED")

    def format_args(self, *args):
        # FIXME: format these correctly
        return f"\t{flags.FC_MODIFIERS[args[0]]} " + " ".join(map(hex, args[1:3]))

_CMD_REF[CmdPred._BYTEVAL] = CmdPred

class Wait(Cmd):
    """
    Signifies that the monster will do nothing this turn.
    """
    _BYTEVAL = 0xFD
    def __init__(self):
        super().__init__(self._BYTEVAL, 0, "WAIT")

_CMD_REF[Wait._BYTEVAL] = Wait

class EndPredBlock(Cmd):
    _BYTEVAL = 0xFE
    def __init__(self):
        super().__init__(self._BYTEVAL, 0, "END FC BLOCK")

_CMD_REF[EndPredBlock._BYTEVAL] = EndPredBlock

class EndBlock(Cmd):
    _BYTEVAL = 0xFF
    def __init__(self):
        super().__init__(self._BYTEVAL, 0, "END BLOCK")

_CMD_REF[EndBlock._BYTEVAL] = EndBlock