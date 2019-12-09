import math
from .expr import Tensor, Par, Var, Unit
from .graph import Graph

def decompose(e, g, row=0):
    if (isinstance(e, Unit)): return range(0,0), row
    v = g.add_vertex(row=row)
    pos, max_v, max_r = knuth_tree_layout(e, g, row, 0, v, 1)
    g.set_position(v, pos / 2)
    vs = range(v, max_v+1)

    for v1 in vs:
        if v1 != v and g.type(v1) == 0:
            g.set_row(v1, max_r)
        if g.type(v1) == 1:
            for e1 in g.out_edges(v1):
                for e2 in g.out_edges(v1):
                    if e1 != e2: g.add_arc(e1, e2, end=0)



    return vs, max_r

def compose(e, g, row=0):
    if (isinstance(e, Unit)): return range(0,0), row
    v = g.add_vertex(row=row)
    pos, max_v, max_r = knuth_tree_layout(e, g, row, 0, v, -1)
    g.set_position(v, pos / 2)
    vs = range(v, max_v+1)

    for v1 in vs:
        if v1 != v and g.type(v1) == 0:
            g.set_row(v1, row)
        else:
            g.set_row(v1, row + (max_r - g.row(v1)))
        if g.type(v1) == 2:
            for e1 in g.in_edges(v1):
                for e2 in g.in_edges(v1):
                    if e1 != e2: g.add_arc(e1, e2, end=1)

    return vs, max_r

def knuth_tree_layout(e, g, row, min_pos, parent_v, edge_dir):
    if (isinstance(e, Unit)): return min_pos, parent_v, row
    row += math.ceil(len(str(e)) / 6)
    v = g.add_vertex(row=row)

    ch = []
    if isinstance(e, Tensor):
        g.set_type(v, 1)
        ch = e.children()
    elif isinstance(e, Par):
        g.set_type(v, 2)
        ch = e.children()
    
    # elif isinstance(e, Var):
    #     if e.dual:
    #         e = ~e
    #         edge_dir *= -1

    if edge_dir == 1:
        g.add_edge(parent_v, v, data = e)
    elif edge_dir == -1:
        g.add_edge(v, parent_v, data = e)

    max_v = v
    max_r = row
    pos = min_pos
    if len(ch) > 0:
        for c in ch:
            pos, max_v0, max_r0 = knuth_tree_layout(c, g, row, pos, v, edge_dir)
            max_v = max(max_v0, max_v)
            max_r = max(max_r0, max_r)
            pos += 1
        pos -= 1

    g.set_position(v, (min_pos + pos) / 2)
    return pos, max_v, max_r


def fuse_var(g):
    g = g.copy()
    fusions = []
    for e0 in g.edges():
        d = g.edata(e0)
        s0,t0 = g.edge_st(e0)

        inp0 = g.type(s0) == 0 and len(g.in_edges(s0)) == 0
        outp0 = g.type(t0) == 0 and len(g.out_edges(t0)) == 0

        if not (isinstance(d, Var) and (inp0 or outp0)):
            continue
            
        for e1 in g.edges():
            s1,t1 = g.edge_st(e1)

            inp1 = g.type(s1) == 0 and len(g.in_edges(s1)) == 0
            outp1 = g.type(t1) == 0 and len(g.out_edges(t1)) == 0

            if not (inp1 or outp1): continue
            
            if g.edata(e1) == d:
                if outp0 and inp1:
                    g1 = g.copy()
                    e2 = g1.add_edge(s0,t1,data=d)
                    g1.copy_arcs(e0, e2)
                    g1.copy_arcs(e1, e2)
                    g1.remove_vertices([t0,s1])
                    fusions.append(g1)
                elif outp1 and inp0:
                    g1 = g.copy()
                    e2 = g1.add_edge(s1,t0,data=d)
                    g1.copy_arcs(e0, e2)
                    g1.copy_arcs(e1, e2)
                    g1.remove_vertices([t1,s0])
                    fusions.append(g1)
            elif g.edata(e1) == ~d:
                if outp0 and outp1:
                    g1 = g.copy()
                    e2 = g1.add_edge(s0,t1,data=d)
                    g1.copy_arcs(e0, e2)
                    g1.set_type(t1, 3)
                    g1.remove_vertices([t0])
                    fusions.append(g1)
                elif inp0 and inp1:
                    g1 = g.copy()
                    e2 = g1.add_edge(s1,t0,data=d)
                    g1.copy_arcs(e0, e2)
                    g1.set_type(s1, 3)
                    g1.remove_vertices([s0])
                    fusions.append(g1)
        if fusions != []: break
            
            # if g.type(s1) == 0 and len(g.in_edges(s1)) == 0:
            #     g.add_edge(s0,t1,data=d)
            #     g.remove_vertices([t0,s1])
            #     return d
    return fusions


def switchings(g):
    sw = []

    def rec(g1):
        g1 = g1.copy() # to normalise edge names
        for v in g1.vertices():
            ie = g1.in_edges(v)
            oe = g1.out_edges(v)
            if len(ie) > 1 and g1.type(v) == 2:
                    for e in ie:
                        g2 = g1.copy()
                        for e1 in ie:
                            if e1 != e and e1 in g2.edges():
                                g2.remove_edge(e1)
                        rec(g2)
                    return
            elif len(oe) > 1 and g1.type(v) == 1:
                    for e in oe:
                        g2 = g1.copy()
                        for e1 in oe:
                            if e1 != e and e1 in g2.edges():
                                g2.remove_edge(e1)
                        rec(g2)
                    return
        sw.append(g1)

    rec(g)
    return sw

def switching_checker(g):
    return all(s.is_acyclic() for s in switchings(g))

def contraction_checker(g):
    g1 = g.copy()
    while (g1.contract1()):
        pass
    return g1.is_point()


def prove(exp0, exp1, checker=None):
    if checker == None:
        checker = switching_checker
    g = Graph()
    vs, row = decompose(exp0, g)
    compose(exp1, g, row)

    def rec(g1):
        fusions = fuse_var(g1)
        if fusions == []:
            if checker(g1):
                return g1
            else:
                return None
        else:
            for f in fusions:
                g2 = rec(f)
                if g2:
                    return g2
            return None
    
    return rec(g)
