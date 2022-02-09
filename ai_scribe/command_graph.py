import math
import random
from collections import defaultdict

import networkx
import numpy

from . import flags
from . import syntax
from . import themes
from .syntax import SYNTAX
from .themes import ELEM_THEMES, STATUS_THEMES, FROM_COMMANDS

# FIXME: to syntax (attached to Cmd?)
def expand(arg_g, cmd_byte=0xF0, nargs=3):
    stack = []

    gptr = arg_g[cmd_byte]
    assert len(gptr) > 0 and set(gptr) != {cmd_byte}
    while len(stack) < nargs:
        try:
            gptr = random.choice(list(gptr))
        except IndexError:
            gptr = cmd_byte

        if gptr != cmd_byte:
            stack.append(gptr)
        gptr = arg_g[gptr]

    return stack

def _bind_token(cmd, script, arg_graph, shuffle_args=False):
    for arg, descr in cmd.parse_args(script):
        arg_graph.add_node(arg, type="generic", descr=descr)
        if shuffle_args:
            arg_graph.add_edge(arg, cmd._BYTEVALUE)

    for a1, a2 in zip(script[:cmd._NARGS-1], script[1:cmd._NARGS]):
        arg_graph.add_edge(a1, a2)

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
            if not d and self_weights.get((u, v), None):
                d.update(self_weights[(u, v)])
            if other.cmd_graph.has_edge(u, v):
                d["weight"] += other.cmd_graph.get_edge_data(u, v).get("weight", 1)

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

    def to_text_repr(self, suppress_args=True):
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
                tstr += f"\n{_n.rjust(16)} -->"
                for v, w in self.cmd_arg_graphs[_name][n].items():
                    if _name in {0xF0, "_"}:
                        try:
                            if _name == v:
                                v = name
                            else:
                                v = flags.SPELL_LIST[v]
                        except TypeError:
                            pass
                    tstr += f" {v}"
                    w = w.get("weight", None)
                    if w is not None:
                        tstr += f" [{w}] "

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

            # FIXME: can we delete this?
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

            if v not in syntax.Cmd._CMD_REG:
                # assume skill command
                script = ["_", v] + script
                continue
            cmd = syntax.Cmd._CMD_REG[v]

            v = "^" if cmd == "^" else cmd._BYTEVAL
            self.cmd_graph.add_node(v, type="command", nbytes=cmd._NARGS, descr=cmd._DESCR)
            self.cmd_graph.add_edge(last_cmd, v)
            self.cmd_graph.get_edge_data(last_cmd, v)["weight"] = \
                self.cmd_graph.get_edge_data(last_cmd, v).get("weight", 0) + 1
            last_cmd = v

            if cmd._NARGS is not None and cmd._NARGS > 0:
                # FIXME: handle this at init
                self.cmd_arg_graphs[v].add_node(v, type="command", nbytes=cmd._NARGS, descr=cmd._DESCR)
                self.cmd_arg_graphs[v].add_edge(v, script[0])

                _bind_token(cmd, script, self.cmd_arg_graphs[v])
                script = script[cmd._NARGS:]

    def validate(self):
        # All graph nodes should be reachable from start
        paths = networkx.shortest_path_length(self.cmd_graph, source="^")
        unreachable = set(self.cmd_graph.nodes) - set(paths)
        if len(unreachable) != 0:
            print(f"Unreachable nodes: {unreachable}")
            print(self.to_text_repr())
        assert len(unreachable) == 0, unreachable

        # No node should be a terminal one
        for node in self.cmd_graph.nodes:
            assert len(self.cmd_graph[node]) != 0, node

    def generate_from_graph(self, start_cmd="^",
                            main_block_len=None, main_block_avg=2, allow_empty_main_blocks=False,
                            disallow_commands=set(), weighted=True, naborts=20, strict=True):
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
        # Adjust the allowed number of aborts for longer scripts
        naborts *= main_block_len

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
                skills = [s for s in skills if s not in syntax.Cmd._CMD_REG]
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


def edit_cmd_arg_graph(cmd_graph, drop_skills={}, drop_nothing=False,
                       add_cmds=None):
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
            #cmd_graph.cmd_graph.remove_node(cmd)
            # It's possible for banned skills like "Escape" to leave dangling
            # Targeting nodes without any outgoing edges, so instead of dropping
            # the command node, we just add "Nothing" as the only possible argument
            subgraph.add_edge(cmd, 0xFE, weight=1)

    # FIXME: sanitize and expand this
    link_nodes = set(cmd_graph.cmd_graph.nodes) - {"^", 0xFE, 0xFF}
    if add_cmds is not None and len(link_nodes) > 0:
        # Create a path so that we're at least assured of an access
        # method for the command
        n1 = random.choice(list(link_nodes))
        n2 = random.choice(list(link_nodes))
        networkx.add_path(cmd_graph.cmd_graph, (n1, 0xF4, n2), weight=1)

        cmd_graph.cmd_arg_graphs[0xF4] = networkx.complete_graph([0xF4] + list(add_cmds))

class RestrictedCommandGraph(CommandGraph):
    @classmethod
    def get_rule_set(cls, *rules, graph=None):
        newg = cls()
        # process rules
        from .scripting import _RULES
        newg.rule_set = {rule: _RULES[rule]()
                            for rule in set(rules) & set(_RULES)}

        if graph:
            newg.cmd_graph = graph.cmd_graph
            newg.cmd_arg_graphs = graph.cmd_arg_graphs

        return newg

    def __init__(self):
        super().__init__()
        self.rule_set = {}

    def check_rules(self, script, **ctx):
        return {name for name, rule in self.rule_set.items()
                    if rule(script, **ctx)}

    # rewrite of generate_from_graph
    def generate_from_graph(self, start_cmd="^",
                            main_block_len=None, main_block_avg=2, allow_empty_main_blocks=False,
                            cntr_block_len=None, cntr_block_avg=1, allow_empty_cntr_blocks=True,
                            disallow_commands=set(), weighted=True, naborts=20, strict=True):

        main_block_avg = None if main_block_avg is None else numpy.random.poisson(main_block_avg)
        main_block_len = main_block_len or main_block_avg
        if not allow_empty_main_blocks and main_block_len == 0:
            main_block_len = 1

        cntr_block_avg = None if cntr_block_avg is None else numpy.random.poisson(cntr_block_avg)
        cntr_block_len = cntr_block_len or cntr_block_avg
        if not allow_empty_cntr_blocks and cntr_block_len == 0:
            cntr_block_len = 1

        # Make a copy, because we can modify the graph in flight
        g = self.cmd_graph.copy()

        # Nullify the outgoing links to block enders
        # NOTE: we don't remove incoming links because they're needed for generation
        g.remove_edges_from([(u, v) for u, v in g.edges if v in {0xFE, 0xFF}])
        # replace some of them with links to "^", e.g. in the case they become terminal
        for node in g.nodes:
            if len(g[node]) == 0:
                g.add_edge(node, "^")

        # TODO: replace these with rule sets
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
                g = networkx.algorithms.minors.contracted_nodes(g, gptr, cmd)

        aborts = defaultdict(lambda: 0)
        while naborts >= 0:
            context = {
                "phase": "main",
                "weighted": weighted,
                "vars_in_use": set(),
                "nfc": 0,
                "ncmd": 0,
                # Allowed number of rule checks per attempt
                "rule_checks": 100
            }
            script, gptr = [], start_cmd
            _script = []
            scr_len = 0

            try:
                while scr_len < main_block_len + cntr_block_len:
                    last = gptr
                    # TODO: have the current command generate the token
                    gptr = self.generate_script_token(g, gptr, script_context=context["phase"])

                    # "Restarting" is allowed, because we replaced block enders earlier
                    if gptr == "^":
                        continue

                    # TODO: variable handling
                    # TODO: formation handling

                    # Need we arguments for command?
                    args = self.generate_cmd_args(gptr, context)

                    _gptr = syntax.Cmd._CMD_REG[gptr]
                    #_gptr = syntax.Cmd[gptr]

                    # Check rules
                    blocking_rules = self.check_rules(_script + [_gptr] + args, **context)

                    # Do rule checking or abort if we're encountering too many
                    if context["rule_checks"] <= 0:
                        raise ValueError(f"Rule application failed too many times.")
                    elif len(blocking_rules) != 0:
                        # TODO: Get rule broken
                        for rule in blocking_rules:
                            aborts[f"rule/{rule}"] += 1
                        # FIXME: we may hit this very quickly if the rejection sampling space is large
                        gptr = last
                        context["rule_checks"] -= 1
                        continue

                    if isinstance(gptr, int):
                        script.extend([gptr] + args)
                    else:
                        # Handle do skill commands
                        script.extend(args)
                    _script.append(_gptr)
                    _script.extend(args)

                    # conditional handling
                    # if we're at the end of the block, conditionals can't be closed, retry
                    if ((context["phase"] == "main" and main_block_len == scr_len + 1) or \
                       (context["phase"] == "counter" and cntr_block_len == scr_len + 1)) and \
                        gptr == syntax.CmdPred._BYTEVAL:
                        raise ValueError("Cannot end block with conditional")
                    # Increasingly likely to end the block
                    # Note that this hardcodes no empty conditionals
                    if random.randint(0, context["nfc"]) > 0 \
                          and last not in {syntax.Targeting._BYTEVAL, syntax.CmdPred._BYTEVAL} \
                          and gptr != syntax.EndPredBlock._BYTEVAL:
                        _gptr = syntax.EndPredBlock
                        gptr = _gptr._BYTEVAL
                        _script.append(_gptr)
                        script.append(gptr)

                    # Track number of useable commands
                    # FIXME: change to syntax objects
                    # FIXME: ncmd should be earlier
                    context["nfc"] += 1 if gptr in {syntax.CmdPred._BYTEVAL} else 0
                    context["ncmd"] += 1 if gptr in {c._BYTEVAL for c in syntax.ATTACK_CMDS} else 0
                    if gptr == syntax.EndPredBlock._BYTEVAL:
                        context["nfc"] = 0

                    # only increment the command counter if
                    # we're not under influence of modifiers
                    if gptr != syntax.Targeting._BYTEVAL:
                        scr_len += 1

                    # End the main block if needed
                    # END BLOCK and END FC BLOCK act the same if we are in a conditional
                    # so this is safe.
                    # TODO: You can save bytes by absorbing the two enders together if they
                    # appear
                    if context["phase"] == "main" and scr_len == main_block_len:
                        _gptr = syntax.EndBlock
                        script.append(_gptr._BYTEVAL)
                        _script.append(_gptr)
                        context["nfc"] = 0
                        context["phase"] = "counter"

            except KeyError as e:
                # Bad command graph links
                # Too many rule applications
                # FIXME: should this be fatal?
                script, gptr = [], start_cmd
                naborts -= 1
                aborts[f"command_graph/bad_links"] += 1
            except ValueError as e:
                script, gptr = [], start_cmd
                naborts -= 1
                # message is often too long / uninformative to embed
                aborts[f"general/{str(e)[:100]}"] += 1
            else:
                # We're done, add script terminator
                script += [syntax.EndBlock._BYTEVAL]
                _script += [syntax.EndBlock]
                # Break out of abort check loop
                break

        import pprint
        if not naborts >= 0:
            exit("Failed to generate script within the prescribe number of attempts. "
                 "Exiting to avoid potential infinite loops. Context:\n"
                 + pprint.pformat(context) +
                 "\nAborts:\n" + pprint.pformat(dict(**aborts)))
        assert naborts >= 0, aborts

        return script

    def generate_script_token(self, g, gptr="^", script_context="main", weighted=True):
        # Things needed for context
        assert script_context in {"main", "counter"}

        if gptr not in g or len(g[gptr]) == 0:
            _gptr = hex(gptr) if isinstance(gptr, int) else gptr
            raise KeyError(f"Current command pointer ({_gptr} / {SYNTAX[gptr][-1]}) "
                           "has no outgoing links. Command graph:\n"
                           + self.to_text_repr())

        # Get our outgoing links
        weights = {c: w.get("weight", 1) for c, w in g[gptr].items()}

        # prune decisions for unusable syntax
        syntax.apply_syntax_rules(gptr, weights)

        # TODO: establish workarounds
        norm = sum(weights.values())
        if norm == 0:
            raise KeyError("gptr has no valid choices."
                           f"\ngptr / weights: {gptr} {weights}"
                           f"\ncommand graph ({len(g)} elements):\n"
                           + self.to_text_repr())

        # If "weighted" is turned on, then we use the appropriately normalized connection weights
        # to assign selection probabilities to each potential next step
        choices = list(weights)
        weights = [(w / norm) if weighted else (1 / len(weighted))
                        for w in weights.values()]

        # We get an index from numpy because they can't be bothered
        # and will *always* convert the input
        # array to one of their overburdened types, so checks for
        # this being a simple int type later fail
        gptr = choices[numpy.random.choice(range(len(weights)), p=weights)]
        return gptr

    def generate_cmd_args(self, gptr, context):
        nargs = SYNTAX[gptr][0]
        args = []
        if gptr in self.cmd_arg_graphs and (nargs or 0) > 0:
            # append arguments
            args = expand(self.cmd_arg_graphs[gptr], gptr, nargs)

        # Track vars in use
        # TODO: move to validation
        if gptr in {0xF8, 0xF9}:
            context["vars_in_use"].add(args[-2])
        if gptr in {0xFC} and args[-3] in {0xC, 0xD, 0x14, 0x15}:
            var = args[-2]
            # FIXME: rearrange to not do this arbitrarily
            # Have FC pointers?
            if len(context["vars_in_use"]) == 0:
                context["vars_in_use"].add(0x0)
            if var not in context["vars_in_use"]:
                var = numpy.random.choice(list(context["vars_in_use"]))

        return args

    def regulate_difficulty(self, init_diff=0, trans_diff=0, ranking={}):
        # 254 is actually 'Nothing', not Lagomorph
        ranking[254] = 1
        # Placeholders, they have a different meaning here
        ranking[syntax.ChooseSpell._BYTEVAL] = 1
        ranking[syntax.DoSkill._BYTEVAL] = 1

        # trans_diff = 0 -> 0 --> chaotic AI (all links equal)
        # trans_diff = inf -> 1
        # higher probability of decreasing in power, increase much less likely
        # trans_diff = -inf -> -1 --> small over large goes to large over small
        # higher probability of increasing in power, decrease much less likely
        trans_diff = 2 * (math.erf(trans_diff) - 0.5)

        # init diff
        init_diff = 2 * (math.erf(init_diff) - 0.5)

        # for CHOOSE_SPELL / DO_SKILL
        for cmd_byte in {syntax.ChooseSpell._BYTEVAL, syntax.DoSkill._BYTEVAL}:
            if self.cmd_arg_graphs.get(cmd_byte, None) is not None:
                arg_g = self.cmd_arg_graphs[cmd_byte]

                weights = {n: max(ranking[n], 1) for n in set(arg_g.nodes) - {cmd_byte}}
                norm = sum([w**init_diff for w in weights.values()])
                weights = {n: max(mpr, 1)**init_diff / norm for n, mpr in weights.items()}
                for n in set(arg_g.nodes) - {cmd_byte}:
                    arg_g.add_edge(cmd_byte, n, weight=weights[n])
                    #print(flags.SPELL_LIST[n], arg_g.edges[cmd_byte, n]["weight"])
                    # FIXME: Need a return weight too

                for u, v in arg_g.edges():
                    if u == cmd_byte or v == cmd_byte:
                        continue
                    small, large = max(1, min(ranking[u], ranking[v])), \
                                   max(max(ranking[u], ranking[v]), 1)
                    arg_g.edges[u, v]["weight"] = (small / large)**trans_diff
                    #print(flags.SPELL_LIST[u], flags.SPELL_LIST[v], small, large, arg_g.edges[u, v]["weight"])

        # TODO: for USE / THROW ITEM


def _augment_cmd_graph(cmd_graph, statuses=set(), elements=set(), commands=set()):
    # Add in a random status/element theme
    for elem in elements:
        elem_g = ELEM_THEMES[elem].copy()
        elem_g.add_edge(0xF0, list(elem_g.nodes)[0])
        cmd_graph.cmd_arg_graphs[0xF0] = \
            networkx.algorithms.compose(elem_g,
                                        cmd_graph.cmd_arg_graphs.get(0xF0, networkx.DiGraph()))

    for stat in statuses:
        stat_g = STATUS_THEMES[stat].copy()
        stat_g.add_edge(0xF0, list(stat_g.nodes)[0])
        cmd_graph.cmd_arg_graphs[0xF0] = \
            networkx.algorithms.compose(STATUS_THEMES[stat],
                                        cmd_graph.cmd_arg_graphs.get(0xF0, networkx.DiGraph()))

    for cmd in commands:
        cmd_g = STATUS_THEMES[cmd].copy()
        cmd_g.add_edge(0xF0, list(cmd_g.nodes)[0])
        cmd_graph.cmd_arg_graphs[0xF0] = \
            networkx.algorithms.compose(FROM_COMMANDS[cmd],
                                        cmd_graph.cmd_arg_graphs.get(0xF0, networkx.DiGraph()))

    return cmd_graph

def augment_cmd_graph(cmd_graph, status=False, elemental=False, command=False):
    return cmd_graph
    # Add in a random status/element theme
    themes, aug_attacks = {}, networkx.DiGraph()
    if elemental:
        themes.update(ELEM_THEMES.copy())
    if status:
        themes.update(STATUS_THEMES.copy())
    if command:
        themes.update(FROM_COMMANDS.copy())

    if len(themes):
        return cmd_graph

    if themes:
        aug_attacks = random.choice([*themes.values()])
    aug_attacks.add_edge(0xF0, list(aug_attacks.nodes)[0])

    cmd_graph.cmd_arg_graphs[0xF0] = \
        networkx.algorithms.compose(aug_attacks, cmd_graph.cmd_arg_graphs[0xF0])

    return cmd_graph