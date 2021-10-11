import random

import networkx
import numpy

from . import flags
from . import syntax
from .syntax import SYNTAX
from .themes import ELEM_THEMES, STATUS_THEMES

def expand(arg_g, cmd_byte=0xF0, nargs=3):
    stack = []

    gptr = arg_g[cmd_byte]
    assert len(gptr) > 0 and set(gptr) != {cmd_byte}
    while len(stack) < nargs:
        try:
            gptr = numpy.random.choice(list(gptr))
        except ValueError:
            gptr = cmd_byte

        if gptr != cmd_byte:
            stack.append(gptr)
        gptr = arg_g[gptr]

    return stack


class CommandGraph:
    def __init__(self):
        # NOTE: we can add arbitrary attributes at the graph level here
        self.cmd_graph = networkx.DiGraph()
        self.cmd_arg_graphs = {cmd: networkx.DiGraph() for cmd in SYNTAX}

        self.OUT_OF_SYNTAX = []

    def __add__(self, other, augment={}):
        self_weights = {(u, v): d for u, v, d in self.cmd_graph.edges(data=True)}

        # Compose together the two command graphs
        self.cmd_graph = networkx.compose(self.cmd_graph, other.cmd_graph)

        # Update weights on connections
        #for (u, v, c) in G.edges.data('color', default='red')
        for u, v, d in self.cmd_graph.edges(data=True):
            print(u, v, d)
            if not d and self_weights.get((u, v), None):
                d.update(self_weights[(u, v)])
            if other.cmd_graph.has_edge(u, v):
                d["weight"] += other.cmd_graph.get_edge_data(u, v).get("weight", 1)
            print(u, v, d)

        # Compose argument graphs
        self.cmd_arg_graphs = {key: networkx.compose(
            self.cmd_arg_graphs.get(key, networkx.Digraph()),
            other.cmd_arg_graphs.get(key, networkx.Digraph()))
            for key in set(self.cmd_arg_graphs) | set(other.cmd_arg_graphs)}

        # Compose with augments
        self.cmd_arg_graphs = {key: networkx.compose(
            self.cmd_arg_graphs.get(key, networkx.Digraph()),
            augment.get(key, networkx.Digraph()))
            for key in set(self.cmd_arg_graphs) | set(augment)}

    def to_text_repr(self, suppress_args=False):
        tstr = ""
        for _name in self.cmd_graph.nodes():
            name = SYNTAX[_name][-1]
            tstr += f"\n{name} [{_name}]: " + " ".join([SYNTAX[n][-1] + f" [{w['weight']}]"
                                              for n, w in self.cmd_graph[_name].items()])
            if suppress_args or _name not in self.cmd_arg_graphs:
                continue
            #for u, v, w in self.cmd_arg_graphs[_name].nodes():
            for n in self.cmd_arg_graphs[_name].nodes():
                _n = str(n)
                if _name in {0xF0, "_"}:
                    try:
                        _n = flags.SPELL_LIST[n] if n != _name else name
                    except TypeError:
                        _n = "UNK"
                tstr += f"\n\t{_n} --[{None}]-->"
                for v, w in self.cmd_arg_graphs[_name][n].items():
                    #w = w.get("weight", None)
                    if _name in {0xF0, "_"}:
                        try:
                            v = flags.SPELL_LIST[v]
                        except TypeError:
                            pass
                    tstr += f" {v}"

        return tstr

    @classmethod
    def merge(cls, *graphs):
        g = graphs.pop(0) if graphs else CommandGraph()
        for other in graphs:
            g += other
        return g

    def visualize(self, fname=None):
        import matplotlib
        matplotlib.use("agg")
        from matplotlib import pyplot
        #fname = fname or f"{self.name}_cmd_graph.png"

        def rename(nlbl):
            node = self.cmd_graph.nodes[nlbl]
            if node.get("type") == "command":
                return nlbl if isinstance(nlbl, str) else hex(nlbl)
            return nlbl
        cgrp = networkx.relabel_nodes(self.cmd_graph, rename)

        for cmd, arg_graph in self.cmd_arg_graphs.items():
            def rename(nlbl):
                node = arg_graph.nodes[nlbl]
                if node.get("type") == "command":
                    return nlbl if isinstance(nlbl, str) else hex(nlbl)
                return nlbl
            # we first have to identify the command node,
            # or else arguments with the same byte values will also
            # be interpreted as command bytes
            arg_graph = networkx.relabel_nodes(arg_graph, rename)
            # connect the graph to its arguments
            cgrp = networkx.compose(cgrp, arg_graph)

        _COLORS = {
            "command": "blue",
            "generic": "red"
        }
        def _fmt_descr(cmd, node):
            d = node.get("descr", hex(cmd) if isinstance(cmd, int) else cmd)
            if "nbytes" in node:
                d += f" [{node['nbytes']}]"
            return d

        node_labels = {k: _fmt_descr(k, d) for k, d in cgrp.nodes.items()}
        node_colors = [_COLORS.get(d.get("type", None), "green")
                                for k, d in cgrp.nodes.items()]

        fig = pyplot.figure(figsize=(20, 20))
        networkx.drawing.draw_networkx(cgrp, node_color=node_colors, labels=node_labels)
        if fname:
            pyplot.savefig(fname)
        return fig

    def from_scripts(self, scripts, on_parse_error='raise'):
        for name, script in list(scripts.items()):
            self.from_script(script)

            if len(self.OUT_OF_SYNTAX) > 0 and on_parse_error is not None:
                v = self.OUT_OF_SYNTAX[-1]
                # FIXME: names seem wrong
                print(f"{name} | Unconsumed byte(s), last [{hex(v)}] corresponding skill: {flags.SPELL_LIST[v]}.\n"
                      f"Script: {script}\n")
                #f"Script so far: {', '.join(map(hex, _script[1:]))}")
                print(self.OUT_OF_SYNTAX)
                #translate(_cpy)
                if on_parse_error == "raise":
                    raise ValueError(f"Unconsumed byte {hex(v)}.")

    def from_script(self, script):
        script = [*script]
        cpy = " ".join([hex(s) for s in script])
        _cpy = bytearray(script)

        #
        # construct the exp-tree
        #
        # beginning marker
        last_cmd = "^"

        # preprocessing:
        while len(script) > 0:
            v = script.pop(0)

            if v not in SYNTAX:
                # assume skill command
                script = ["_", v] + script
                continue

            if v in SYNTAX:
                nbytes, _, descr = SYNTAX[v]
            else:
                nbytes, descr = None, None
                self.OUT_OF_SYNTAX.append(v)

            self.cmd_graph.add_node(v, type="command", nbytes=nbytes, descr=descr)
            self.cmd_graph.add_edge(last_cmd, v)
            self.cmd_graph.get_edge_data(last_cmd, v)["weight"] = \
                self.cmd_graph.get_edge_data(last_cmd, v).get("weight", 0) + 1
            last_cmd = v

            if nbytes is not None and nbytes > 0:
                from . import syntax
                cmd_obj = syntax._CMD_REF.get(v, None)
                if cmd_obj is not None:
                    types = cmd_obj()._argument_types
                    shuffle_args = cmd_obj().arg_shuffle_allowed
                else:
                    types = [None] * nbytes
                    shuffle_args = False

                # FIXME: handle this at init
                self.cmd_arg_graphs[v].add_node(v, type="command", nbytes=nbytes, descr=descr)
                self.cmd_arg_graphs[v].add_edge(v, script[0])
                i = 0
                for a, t in zip(script[:nbytes], types):
                    i += 1
                    try:
                        descr = t[a] if isinstance(t, (dict, list)) else t(a)
                        self.cmd_arg_graphs[v].add_node(a, type="generic", descr=descr)
                    except TypeError:
                        pass
                    except KeyError:
                        # There's at least one missing targeting byte description
                        pass
                    if shuffle_args:
                        self.cmd_arg_graphs[v].add_edge(a, v)

                for a1, a2 in zip(script[:nbytes - 1], script[1:nbytes]):
                    self.cmd_arg_graphs[v].add_edge(a1, a2)
                script = script[nbytes:]

    def generate_from_graph(self, start_cmd="^",
                            main_block_len=None, main_block_avg=2, allow_empty_main_blocks=False,
                            disallow_commands={}, weighted=True, naborts=20, strict=True):
        import numpy
        script = []

        # Make a copy, because we can modify the graph in flight
        g = self.cmd_graph.copy()

        # Handle disallowed commands
        # Basically, we're 'contracting' the graph by allowing the jump to 'skip'
        # over the disallowed command, while preserving the ability to jump to
        # outgoing connections of the disallowed node itself
        for gptr in set(g.nodes) - disallow_commands:
            for cmd in set(g[gptr]) & disallow_commands:
                # The contraction process, by default, changes edges between u and v into self loops
                # on the linked node. While it's not fatal to have this behavior, to keep things
                # a bit cleaner, we'll ensure the link to the start char is broken before the contraction
                # so that no self-loops on the start cmd happen
                if start_cmd in g[cmd]:
                    g.remove_edge(cmd, start_cmd)
                if cmd in g[start_cmd]:
                    g.remove_edge(start_cmd, cmd)
                # This contracts for only this node, and it's a permanent change for this run through
                #print(self.cmd_graph.edges)
                g = networkx.algorithms.minors.contracted_nodes(g, gptr, cmd)
                #print(gptr, cmd, g.edges)

        # We also have to break a potential link between 0xFC and 0xF{E,F} so we don't try and create
        # empty FC blocks

        # NOTE: This order is bad since contractions from above may cause a
        # 0xFC -> 0xFE -> 0xFF chain which it then discards the right two links
        # and there's no way to end the counter block
        # FIXME: doesn't really work with strict mode and contractions
        #if 0xFC in g and 0xFE in g:
            #g = networkx.algorithms.minors.contracted_nodes(g, 0xFC, 0xFE)
        #if 0xFC in g and 0xFF in g:
            #g = networkx.algorithms.minors.contracted_nodes(g, 0xFC, 0xFF)

        # This is needed or the counter block generation will never end
        assert 0xFF in g and len(g.in_edges(0xFF)) > 0

        gptr = start_cmd
        nff, nfc, ncmd = 0, 0, 0
        vars_in_use = set()

        main_block_avg = None if main_block_avg is None else numpy.random.poisson(main_block_avg)
        main_block_len = main_block_len or main_block_avg
        if not allow_empty_main_blocks and main_block_len == 0:
            main_block_len = 1

        from collections import defaultdict
        aborts = defaultdict(lambda: 0)
        #while nff < 2:
        while nff < 2 and naborts >= 0:
            last = gptr
            if gptr not in g or len(g[gptr]) == 0:
                #raise ValueError(f"Command Node {gptr} has no outgoing connections.")
                # We reset as a backup
                gptr = start_cmd

            # Select the next command to jump to
            if len(g[gptr]) > 0:
                gptr = g[gptr]
            else:
                raise SyntaxError(f"Current command pointer ({hex(gptr)} / {SYNTAX[gptr]}) "
                                  "has no outgoing links. " + str(g[gptr]))

            # If "weighted" is turned on, then we use the appropriately normalized connection weights
            # to assign selection probabilities to each potential next step
            if weighted:
                gptr = {c: w.get("weight", 1) for c, w in gptr.items()}
                # enforce command block length requirement
                # FIXME: we'll need to something similar for the counter block
                if nff == 0:
                    gptr.pop(0xFF, None)
                    # It's possible for the command graph to have a node with only an
                    # outgoing connection to 0xFF
                    if len(gptr) == 0:
                        gptr = start_cmd
                        continue
                weights = sum(gptr.values())
                weights = [w / weights for w in gptr.values()]
            else:
                weights = [1 / len(gptr)] * len(gptr)
            try:
                gptr = numpy.random.choice(list(gptr), p=weights)
            except:
                raise SyntaxError("gptr has no valid choices. Current script is:\n" +
                                  " ".join(map(hex, script)) +
                                  f"\ngptr / weights: {gptr} {weights}"
                                  f"\ncommand graph ({len(g)} elements): {str(g.edges)}")

            # catch '_'
            try:
                gptr = int(gptr)
            except ValueError:
                pass

            # graph bypasses
            if nff == 0 and ncmd >= main_block_len:
                # End main block with specified number of commands
                gptr = 0xFF
            # Disabled since the generation should take care of this on its own now, see above
            #elif main_block_len is None and numpy.random.randint(0, 10) < nff + 1:
                # Roughly increasing probability of ending the block / script
                #gptr = 0xFF
            elif numpy.random.randint(0, 3) < nfc and nfc > 0 and script[-4] != 0xFC and script[-2] != 0xF1:
                # The more times we add command predicates, the more likely we are
                # to end the block, but avoid empty FC blocks
                gptr = 0xFE

            # Can't have an end FC block without active command predicates
            if gptr == 0xFE and nfc == 0:
                if strict:
                    exit("GENERATION: EXCEPTION bad FC block end")
                aborts["bad FC block end"] += 1
                naborts -= 1
                continue

            # End / Reset blocks
            if gptr in {0xFE, 0xFF}:
                # Close the block as long as we don't have an empty FC block
                if nfc > 0 and last == 0xFC:
                    if strict:
                        exit(f"GENERATION: ABORT empty FC {hex(gptr)} {nfc}")
                    aborts["empty FC"] += 1
                    naborts -= 1
                    continue
                # Don't leave a dangling target command
                if len(script) >= 2 and last == 0xF1:
                    if strict:
                        exit("GENERATION: ABORT dangling target")
                    gptr = 0xF1
                    aborts["dangling target"] += 1
                    naborts -= 1
                    continue
                nfc = 0

            if gptr == 0xFF:
                nff += 1
            elif gptr == 0xFC:
                nfc += 1

            # catch '_'
            try:
                gptr = int(gptr)
                script.append(gptr)
            except ValueError:
                pass

            # Need we arguments to command?
            nargs = SYNTAX[gptr][0]
            if gptr in self.cmd_arg_graphs and (nargs or 0) > 0:
                # append arguments
                script.extend(expand(self.cmd_arg_graphs[gptr], gptr, nargs))

            # Track vars in use
            if gptr in {0xF8, 0xF9}:
                vars_in_use.add(script[-2])
            if gptr in {0xFC} and script[-3] in {0xC, 0xD, 0x14, 0x15}:
                var = script[-2]
                # FIXME: rearrange to not do this arbitrarily
                # Have FC pointers?
                if len(vars_in_use) == 0:
                    vars_in_use.add(0x0)
                if var not in vars_in_use:
                    var = numpy.random.choice(list(vars_in_use))

            # Track number of useable commands
            if gptr in {0xF0, 0xF4, 0xF6, "_"}:
                ncmd += 1

        if not (nff == 2 and naborts >= 0):
            exit("Failed to generate script within the prescribe number of attempts. "
                 "Exiting to avoid potential infinite loops")

        assert nff == 2 and naborts >= 0, (nff, aborts)
        return script

    def generate_from_template(self, script, required={}, drop_events={}):
        script = [*script]

        # end marker
        script.append("$")

        # preprocessing:
        while script[0] != "$":
            v = script.pop(0)

            if v not in SYNTAX:
                # assume skill command
                skills = list(self.cmd_arg_graphs.get(0xF0, [0xF0, 0xEE]))[1:]
                skills += list(self.cmd_arg_graphs.get("_", ["_"]))[1:]
                skills = [s for s in skills if s not in syntax._CMD_REF]
                script.append(random.choice(skills))
                continue

            nbytes, _, descr = SYNTAX[v]
            nbytes = nbytes or 0

            args, script = script[:nbytes], script[nbytes:]

            if v not in required and nbytes > 0:
                # generate new arguments
                args = expand(self.cmd_arg_graphs[v], v, nbytes)

            # Drop certain events
            if v == 0xF7 and args[0] in drop_events:
                continue

            script.append(v)
            script.extend(args)

        return script[1:]


def edit_cmd_arg_graph(cmd_graph, drop_skills={}, drop_nothing=False):
    # remove "Nothing" from CHOOSE SPELL
    if drop_nothing:
        cmd_graph.cmd_arg_graphs[0xF0].remove_nodes_from([0xFE])

    # remove banned skills
    for cmd in {0xF0, "_"}:
        # Leave the command in, as it roots the argument graph
        # it will get filtered in expand
        subgraph = cmd_graph.cmd_arg_graphs[cmd]
        subgraph.remove_nodes_from(drop_skills - {cmd})
        if len(subgraph.nodes) <= 1 and cmd in cmd_graph.cmd_graph:
           cmd_graph.cmd_graph.remove_node(cmd)


def augment_cmd_graph(cmd_graph, status=False, elemental=False):
    # Add in a random status/element theme
    themes, aug_attacks = {}, networkx.DiGraph()
    if elemental:
        themes.update(ELEM_THEMES.copy())
    if status:
        themes.update(STATUS_THEMES.copy())

    if themes:
        aug_attacks = random.choice([*themes.values()])
    aug_attacks.add_edge(0xF0, list(aug_attacks.nodes)[0])

    cmd_graph.cmd_arg_graphs[0xF0] = \
        networkx.algorithms.compose(aug_attacks, cmd_graph.cmd_arg_graphs[0xF0])

    return cmd_graph