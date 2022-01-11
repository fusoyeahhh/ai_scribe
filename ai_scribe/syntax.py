import numpy
from . import flags

# TODO: hunt down uses of this and replace appropriately
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

DO_SKILL = "_"
BEGIN_SCRIPT = "^"

#
# Hard rules for transitions
#

def apply_syntax_rules(gptr, weights):
    """
    Identify and eliminate syntactically valid, but completely impractical situations
    """
    # For now, nullify the ability to end the block, this may change later
    if EndBlock._BYTEVAL in weights:
        weights[EndBlock._BYTEVAL] = 0
    if EndPredBlock._BYTEVAL in weights:
        weights[EndPredBlock._BYTEVAL] = 0
    # 0xFC cannot go to 0xFE, 0xFF (empty conditional)
    if gptr == CmdPred._BYTEVAL:
        weights[EndPredBlock._BYTEVAL] = 0
    # 0xFF, 0xFE cannot go to 0xFE (bad syntax)
    if gptr in {EndBlock._BYTEVAL, EndPredBlock._BYTEVAL}:
        weights[EndPredBlock._BYTEVAL] = 0
    # 0xF1 must be followed by something valid (an attack)
    if gptr == Targeting._BYTEVAL:
        for cmd in weights:
            if cmd not in set(c._BYTEVAL for c in Targeting.VALID_TARGETABLE):
                weights[cmd] = 0

class Cmd:
    _CMD_REG = {}

    _BYTEVAL = None
    _NARGS = None
    _DESCR = None
    _ALLOWED_ARGS = ...

    @classmethod
    def __init_subclass__(cls, **kwargs):
        if cls._BYTEVAL in Cmd._CMD_REG:
            raise ValueError(f"Command {cls} registered with {hex(cls._BYTEVAL)} cannot be defined. "
                             f"{hex(cls._BYTEVAL)} is already registered as {Cmd._CMD_REG[cls._BYTEVAL]}")

        cls._BYTEVAL = kwargs.pop("byteval", cls._BYTEVAL)
        cls._NARGS = kwargs.pop("nargs", cls._NARGS)
        cls._DESCR = kwargs.pop("descr", cls._DESCR)
        cls._ALLOWED_ARGS = kwargs.pop("allowed_args", cls._ALLOWED_ARGS)

        Cmd._CMD_REG[cls._BYTEVAL] = cls
        return cls

    @classmethod
    def __getitem__(cls, byteval):
        return Cmd._CMD_REG[byteval]

    @classmethod
    def scan(cls, script):
        cmdmap = {}
        idx = script.find(cls._BYTEVAL)
        while idx != -1:
            cmdmap[idx] = script[idx:idx + cls._NARGS]
        return cmdmap

    @classmethod
    def parse_args(cls, script):
        return [(arg, None) for arg in script[:cls._NARGS]]

    @classmethod
    def format_args(cls, *args, joiner=" | "):
        return joiner.join([*map(str, args)])

    @classmethod
    def validate_args(cls, *args, left=None):
        cls.parse_args(args)
        return True

    @classmethod
    def to_str(cls):
        return f"[{hex(cls._BYTEVAL)}] {cls._DESCR}\n"

    @classmethod
    def expand(cls, arg_g, virtual=False):
        """
        Expand the command into its randomized parameters with argument graph `arg_g`.

        :param arg_g: `networkx.DiGraph` a graph containing the relationships between the parameters; must include the command byte as well
        :param virtual: `bool` Command is not actually in syntax, so do not prepend it to result
        :return: a `list` of byte values corresponding to the command parameters
        """
        # We may not need the syntax marker
        stack = [] if virtual else [cls._BYTEVAL]

        gptr = arg_g[cls._BYTEVAL]
        while len(stack) < (cls._NARGS or 0):
            try:
                gptr = numpy.random.choice(list(gptr))
                stack.append(gptr)
            except ValueError:
                gptr = cls._BYTEVAL

            gptr = arg_g[gptr]

        return stack

    def __init__(self, *args):
        self._args = args

    def __call_(self, rhs):
        # apply rules
        return True

class ChooseSpell(Cmd, byteval=0xF0, nargs=3, descr="CHOOSE SPELL",
                       allowed_args=set(range(0x100))):
    """
    Randomly selects a skill to perform from the next three bytes.
    """
    @classmethod
    def parse_args(cls, script):
        return [(arg, flags.SPELL_LIST[arg]) for arg in script[:cls._NARGS]]

    @classmethod
    def format_args(cls, *args):
        return Cmd.format_args(*[flags.SPELL_LIST[arg] for arg in args])

    @classmethod
    def validate_args(cls, *args, left=None):
        return set(args).issubset(cls._ALLOWED_ARGS)

    @classmethod
    def expand(cls, arg_g):
        arg = super().expand(arg_g)
        if any(arg not in cls._ALLOWED_ARGS for arg in arg[1:]):
            raise
        return arg

class DoSkill(Cmd, byteval="_", nargs=1, descr="DO SKILL",
                   allowed_args=ChooseSpell._ALLOWED_ARGS - set(range(0xF0, 0x100))):
    """
    Unconditionally perform the specified skill.

    NOTE: this is not an actual byte-valued command. It is a placeholder so that
    the script parser does not confuse it for other commands or their parameters.
    """
    @classmethod
    def expand(cls, arg_g):
        Cmd.format_args(arg_g, virtual=True)

    @classmethod
    def validate_args(cls, *args, left=None):
        return set(args).issubset(cls._ALLOWED_ARGS)

    @classmethod
    def format_args(cls, *args):
        return flags.SPELL_LIST[args[0]]

class ChangeFormation(Cmd, byteval=0xF2, nargs=3, descr="CHANGE FORMATION",
                           # FIXME: how many allowed formations?
                           allowed_args=set(range(0x1FF))):
    """
    Used to switch between formations.

    Parameters: [unknown = 0] [formation byte 1] [formation byte 2]

    From the scripting guide:
    The first bit of last byte determines if the monsters should get Max HP or not.
    If it's 1, then the monsters get max HP.
    If it's 0, then monsters retain HP and max HP from current formation.
    """
    _HP_MASK = 1 << 15
    @classmethod
    def format_args(cls, *args):
        form = int.from_bytes(args[1:3], "little")
        with_hp = (form & cls._HP_MASK) == cls._HP_MASK
        form = ((form << 1) & 0xFFFF) >> 1
        with_hp = " WITH MAX HP" if with_hp else ""
        return hex(form) + with_hp

    # TODO: argument checking
    @classmethod
    def validate_args(cls, *args, left=None):
        return set(args).issubset(cls._ALLOWED_ARGS)

class DisplayMsg(Cmd, byteval=0xF3, nargs=2, descr="DISPLAY MESSAGE",
                      # FIXME: get from module
                      allowed_args=set(range(0x1FF))):
    """
    Display a message indicated by the next two bytes.
    """
    @classmethod
    def format_args(cls, *args, msg_dict={}):
        form = int.from_bytes(args[1:3], "little")
        if form in msg_dict:
            return f"{hex(form)} = \"{msg_dict[form]}\""
        return hex(form)

    # FIXME: make generic in Cmd
    def validate_args(self, *args, left=None):
        return set(args).issubset(self._ALLOWED_ARGS)

class UseCommand(Cmd, byteval=0xF4, nargs=3, descr="USE COMMAND",
                      allowed_args=flags.CMD_LIST):
    """
    Execute a command chosen randomly from the next three bytes.

    NOTE: Not all commands work properly.
    """
    _VALID_COMMANDS = {f for f, s in flags.CMD_LIST.items()
                            if s.startswith("(") or s == "Nothing"}
    def format_args(cls, *args):
        return Cmd.format_args([flags.CMD_LIST.get(arg, "{ILLEGAL}") for arg in args])

    @classmethod
    def validate_args(cls, *args, left=None):
        # Many commands are syntactically valid, but do not produce
        # a valid or interesting effect
        return set(args).issubset(cls._VALID_COMMANDS)

class AlterFormation(Cmd, byteval=0xF5, nargs=3, descr="ALTER FORMATION"):
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
    _STATUS = {
        0: "SHOWN AND KILLED(?)",
        1: "KILLED",
        2: "SHOWN",
        3: "HIDDEN AT MAX HP",
        4: "HIDDEN"
    }

    _VALID_ANIM = {arg: k for k, arg in enumerate(flags.ANIMATIONS)}
    _DIE_LIKE_A_BOSS = [0x0B, 0x1, 0xFF]

    @classmethod
    def format_args(cls, *args):
        anim = flags.ENT_ANIMATIONS[args[0]]
        status = cls._STATUS.get(args[1], "???")
        return f"{anim} {status} {bin(args[2])}"

    # FIXME
    @classmethod
    def validate_args(cls, *args, left=None):
        super().validate_args(*args, left)
        #status = cls._STATUS.get(args[1], "???")
        #return status in cls._STATUS set(args).issubset(cls._VALID_COMMANDS)

class ThrowUseItem(Cmd, byteval=0xF6, nargs=3, descr="THROW / USE ITEM",
                        allowed_args={0, 1}):
    """
    Throw or use (first byte) randomly selected item from next two bytes

    [0 = use | 1 = throw] [item1] [item2]
    """
    _VALID_ITEMS = set(flags.ITEM_LIST)

    @classmethod
    def format_args(cls, *args):
        toggle = 'use' if args[0] == 0 else 'throw'
        args = [flags.ITEM_LIST[i] for i in args]
        return f"{toggle} " + Cmd.format_args(*args)

    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._ALLOWED_ARGS \
               and set(args[1:]).issubset(cls._VALID_ITEMS)


class Targeting(Cmd, byteval=0xF1, nargs=1, descr="TARGETTING",
                allowed_args=flags.TARGET_LIST):
    """
    The next attack will use the target specified by the byte after this.
    """
    VALID_TARGETABLE = (DoSkill, ChooseSpell, ThrowUseItem, UseCommand)

    @classmethod
    def format_args(cls, *args):
        return Cmd.format_args(flags.TARGET_LIST.get(args[0], f"<UNK>"))

    @classmethod
    def validate_args(cls, *args, left=None):
        return set(args).issubset(cls._ALLOWED_ARGS)

class SpecialEvent(Cmd, byteval=0xF7, nargs=1, descr="SPECIAL EVENT",
                        # FIXME: need event list
                        allowed_args=set(flags.SPECIAL_EVENTS)):
    """
    Trigger a special in-battle event specified by next byte.

    [event]
    """
    @classmethod
    def format_args(cls, *args):
        if args[0] in flags.SPECIAL_EVENTS:
            return f"{hex(args[0])} " + flags.SPECIAL_EVENTS[args[0]]
        return f"{hex(args[0])}"

class VariableBase():
    """
    Provides a (global) common base by which script variables can be created and tracked.
    """

    __VARIABLE_CONTEXT = set()

    @classmethod
    def reset(cls):
        cls.__VARIABLE_CONTEXT = set()

    @classmethod
    def get_random_var(cls):
        pass

    @classmethod
    def register_var(cls):
        pass

class VarMath(Cmd, VariableBase, byteval=0xF8, nargs=2, descr="VAR MATH"):
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

    @classmethod
    def format_args(cls, *args):
        oper = cls._oper(args[1])
        val = args[1] & 0x3F
        return f"var {hex(args[0])}: {oper} {val}"

    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._VALID_OPERS and set(args[1:]).issubset(cls._ALLOWED_ARGS)

class VarManip(Cmd, VariableBase, byteval=0xF9, nargs=3, descr="VAR MANIP"):
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
    _VALID_OPERS = {
        0: "TOGGLE",
        1: "SET",
        2: "CLEAR"
    }

    @classmethod
    def _oper(cls, value):
        return cls._VALID_OPERS.get(value, "???")

    @classmethod
    def format_args(cls, *args):
        oper = cls._oper(args[0])
        val = args[1] & 0x3F
        return f"var {hex(args[1])}: {oper} {val}"

    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._VALID_OPERS and set(args[1:]).issubset(cls._ALLOWED_ARGS)

class SpecAct(Cmd, byteval=0xFA, nargs=3, descr="SPECIAL ACTION"):
    """
    Animation effects, specified by next byte, targeting the byte thereafter.

    [animation id] [target] [unk.]
    """
    _VALID_ANIM = {anim: i for i, anim in enumerate(flags.ANIMATIONS)}
    _VALID_TARGETS = set(flags.TARGET_LIST)

    @classmethod
    def format_args(cls, *args):
        # FIXME: find out what's going on here, it's part of Telstar's script
        # Might be a sound of some kind
        if args[0] == cls._VALID_ANIM["Unknown"]:
            return f"{flags.ANIMATIONS[args[0]]} {hex(args[1])} [{hex(args[2])}]"
        return f"{flags.ANIMATIONS[args[0]]} {flags.TARGET_LIST[args[1]]} [{hex(args[2])}]"

    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._VALID_ANIM and args[0] in cls._VALID_TARGETS

class Misc(Cmd, byteval=0xFB, nargs=2, descr="MISC."):
    """
    Miscellaneous effects, specified by next byte, targeting the byte thereafter.

    [effect] [target]
    """
    _VALID_MISC = set(flags.MISC)
    _VALID_TARGETS = set(flags.TARGET_LIST)
    _STATUS_BYTES = {0x0B, 0x0C}
    _VALID_STATUS = {
        0: "Blind", 1: "Zombie", 2: "Poison", 3: "M-Tek",
        4: "Invisible", 5: "Imp", 6: "Stone", 7: "Death",
        8: "Condemned", 9: "Weak", 0xA: "Image", 0xB: "Mute",
        0xC: "Berserk", 0xD: "Confuse", 0xE: "Seizure", 0xF: "Sleep",
        0x10: "Dance", 0x11: "Regen", 0x12: "Slow", 0x13: "Haste",
        0x14: "Stop", 0x15: "Shell", 0x16: "Safe", 0x17: "Reflect"
    }
    @classmethod
    def format_args(cls, *args):
        if args[0] in cls._STATUS_BYTES:
            return f"{flags.MISC[args[0]]} {cls._VALID_STATUS[args[1]]}"
        # FIXME: This isn't listed in the guide, it's part of Piranha's script
        elif args[0] == 0xD:
            return f"???? {hex(args[1])}"
        return f"{flags.MISC[args[0]]} {flags.TARGET_LIST[args[1]]}"

    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._VALID_MISC and args[0] in cls._VALID_TARGETS

class CmdPred(Cmd, VariableBase, byteval=0xFC, nargs=3, descr="CMD PRED"):
    """
    Predicate all actions on the evaluated truth value of this command until the block is ended.

    [modifier type] [param1] [param2]
    NOTE: This can be ended by 0xFE or OxFF.
    """
    _VALID_MODS = flags.FC_MODIFIERS
    _PRED_ARGS = {arg: k for k, arg in enumerate(flags.PRED_ARGS)}

    _IF_SELF_DEAD = [_PRED_ARGS["IS DEAD"], 0x0, 0x0]

    @classmethod
    def format_args(cls, *args):
        # FIXME: format these correctly
        name = flags.FC_MODIFIERS[args[0]]
        _args = []
        for mod, arg in zip(flags.PRED_ARGS[name], args[1:]):
            try:
                _args.append(str(mod[arg]))
                continue
            except (KeyError, TypeError):
                pass
            try:
                _args.append(str(mod(arg)))
                continue
            except TypeError:
                pass
            _args.append(f"<{str(arg)}>")
        return f"{name} " + " ".join(_args)

    # TODO: these will need some work, and may need subclasses
    @classmethod
    def validate_args(cls, *args, left=None):
        return args[0] in cls._VALID_MODS and ...

class Wait(Cmd, byteval=0xFD, nargs=0, descr="WAIT"):
    """
    Signifies that the monster will do nothing this turn.
    """
    pass

class EndPredBlock(Cmd, byteval=0xFE, nargs=0, descr="END FC BLOCK"):
    """
    Ends the influence of the most recent predicate.
    """
    pass

class EndBlock(Cmd, byteval=0xFF, nargs=0, descr="END BLOCK"):
    """
    Signifies closing of the current block.
    """
    pass

ATTACK_CMDS = {ChooseSpell, ThrowUseItem, UseCommand, DoSkill}