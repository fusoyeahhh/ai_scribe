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
