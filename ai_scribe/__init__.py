from . import command_graph
from . import scripting
from .extract import *
from .pack import _validate, randomize_scripts

from .themes import AREA_SETS, STATUS_THEMES, ELEM_THEMES, BOSSES

# These enemies do not have names in the ROM
_NAME_ALIASES = {

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

def edit_cmd_arg_graph(cmd_graph, drop_skills={}, drop_nothing=False):
    # remove "Nothing" from CHOOSE SPELL
    if drop_nothing:
        cmd_graph.cmd_arg_graphs[0xF0].remove_nodes_from([0xFE])
    # remove "Escape" for now
    for cmd in {0xF0, "_"}:
        cmd_graph.cmd_arg_graphs[cmd].remove_nodes_from(drop_skills)
