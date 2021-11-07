import random
import networkx

# We want the connection probability to be conditioned on the
# spell power

# FIXME: make this work
def generate_element_theme(_elem, skills, scale=0, skew=1):
    g = networkx.DiGraph()
    # anchor = skills.loc[_elem.index].index[0]

    diff = 4.2

    import math
    frac_part, diff = math.frexp(diff)

    location = diff / 255

    locality = frac_part
    # translate to -1 - 1
    locality = 2 * frac_part - 1
    diff = 2 * frac_part - 1

    if diff > 0:
        diff = 1. / diff
    rnd = 1 / random.randint(0, len(skills)) ** diff

    # locality
    location + abs(rnd - location) ** locality

    for i, skill in skills.loc[_elem.index].iterrows():
        p1 = skill["Power"]
        for i2, skill2 in skills.loc[_elem.index].iterrows():
            p2 = skill2["Power"]
            if p2 < p1:
                continue
            # if random.randint(0, p2) < p1:
            # if beta(scale, skew).rvs() < p1 / p2:
            if beta(scale, skew).rvs() < random.uniform():
                g.add_edge(i, i2)
        # if random.uniform(0, 1) < min(p1, 128) / 128:
        # g.add_edge(i, anchor)

    return g
# ELEM_THEMES["_" + elem] = generate_element_theme()


def generate_status_theme(skills, _status):
    g = networkx.DiGraph()
    for i, skill in skills.loc[_status.index].iterrows():
        p1 = skill["Power"]
        for i2, skill2 in skills.loc[_status.index].iterrows():
            p2 = skill2["Power"]
            if p2 < p1:
                continue
            if random.randint(0, p2) < p1:
                g.add_edge(i, i2)

def to_script_nodes(script):
    from .scripting import _CMD_REF,
    from .syntax import SYNTAX
    script = [*script].copy()

    cmd_nodes = []
    while len(script) > 0:
        v = script.pop(0)

        cmd_node = _CMD_REF["_"]() if v not in SYNTAX else _CMD_REF[v]()
        script = cmd_node.consume_args(script)
        cmd_nodes.append(cmd_node)

    return cmd_nodes

try:
    """
    from colorama import init, Fore, Back, Style
    COLORIZE = {
        0xF0: (Fore.BLUE, Style.RESET_ALL),
        0xFC: (Style.BRIGHT + Fore.GREEN, Style.RESET_ALL),
        0xFD: (Style.DIM, Style.RESET_ALL),
        0xFE: (Fore.LIGHTGREEN, Style.RESET_ALL),
        0xFF: (Back.WHITE, + Fore.BLACK, Style.RESET_ALL)
    }
    """
except ImportError:
    #log.warning("Colorized output requires 'colorama' to be installed. Proceeding without.")
    COLORIZE = {}
    def translate(script, memblk=False, allow_partial=False, colorize=False):
        pass


class Cmd:
    """
    Abstraction of a script command and its arguments. Used as nodes in more complicated scripting constructions.
    """

    def translate_args(self, *args):
        for a, t in zip(args, self._argument_types):
            try:
                descr = t[a] if isinstance(t, (dict, list)) else t(a)
            except TypeError:
                pass
            except KeyError:
                # There's at least one missing targeting byte description
                pass
        return descr

    def consume_args(self, scr_bytes):
        """
        Consume the requisite number of bytes from the script to determine the arguments to the command byte.
        """
        return scr_bytes[:self.nargs]


class ScriptFragment:
    """
    Compositions of script fragments.
    """
    _variables = {}

    def __init__(self, byteval, descr):
        self.byteval = byteval
        self.descr = descr

    @classmethod
    def register_variable(cls, var):
        if var in ScriptFragment._variables:
            raise ValueError(f"{var} is already registered.")
        ScriptFragment._variables[var] = None

    @classmethod
    def acquire_new_variable(cls):
        # FIXME: how many variable registers do we have?
        for i in range(255):
            if i not in ScriptFragment._variables:
                ScriptFragment.register_variable(i)
                return i

        raise ValueError("No variable registers available.")

    def expand(self):
        pass

    def to_script(self):
        pass

class OneTimeTrigger(ScriptFragment):
    def __init__(self):
        fire_once = [*b'\xfc\x15\x03\x00\xf9\x00\x03\x00']
        script = [CmdPred(), VarManip()]
        super()
