# HOCC - Python library for higher order causal categories
# Copyright (C) 2019 - Aleks Kissinger

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import abc
from fractions import Fraction
import math
import cmath
import copy


class Graph(object):
    """Basic open graph implementation, with vertex and edge data."""
    backend = 'None'

    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.graph = dict()
        self._source = dict()
        self._target = dict()
        self._vindex = 0
        self._eindex = 0
        self._arcs = dict()
        self._num_arcs = 0

        self.ty = dict()
        self._pindex = dict()
        self._maxp = -1
        self._rindex = dict()
        self._maxr = -1
        
        self._vdata = dict()
        self._edata = dict()

    def __str__(self):
        return "Graph({} {}, {} {}, {} {})".format(
                str(self.num_vertices()),
                'vertex' if self.num_vertices() == 1 else 'vertices',
                str(self.num_edges()),
                'edge' if self.num_edges() == 1 else 'edges',
                str(self.num_arcs()),
                'arc' if self.num_arcs() == 1 else 'arcs')

    def __repr__(self):
        return str(self)

    def stats(self):
        s = str(self) + "\n"
        degrees = {}
        for v in self.vertices():
            d = self.vertex_degree(v)
            if d in degrees: degrees[d] += 1
            else: degrees[d] = 1
        s += "degree distribution: \n"
        for d, n in sorted(degrees.items(),key=lambda x: x[0]):
            s += "{:d}: {:d}\n".format(d,n)
        return s

    def copy(self, dual=False, backend=None):
        """Create a copy of the graph. If ``dual`` is set, 
        the duel of the graph will be returned (inputs and outputs flipped, types dualised).
        """
        g = Graph()

        #g.add_vertices(self.num_vertices())
        ty = self.types()
        ps = self.positions()
        rs = self.rows()
        maxr = self.depth()
        vtab = dict()
        for v in self.vertices():
            v1 = g.add_vertex(ty[v])
            if v in ps: g.set_position(v1,ps[v])
            if v in rs: 
                if dual: g.set_row(v1, maxr-rs[v])
                else: g.set_row(v1, rs[v])
            vtab[v] = v1
            if v in self._vdata:
                g.set_vdata(v1, self._vdata[v])

        for i in self.inputs:
            if dual: g.outputs.append(vtab[i])
            else: g.inputs.append(vtab[i])
        for o in self.outputs:
            if dual: g.inputs.append(vtab[o])
            else: g.outputs.append(vtab[o])
        
        etab = dict()
        for e in self.edges():
            s,t = self.edge_st(e)
            e1 = g.add_edge(vtab[s], vtab[t])
            etab[e] = e1
            if e in self._edata:
                g.set_edata(e1, self._edata[e])

        for e1,e2,at_v in self.arcs():
            g.add_arc(etab[e1], etab[e2], vtab[at_v])

        return g

    def dual(self):
        """Returns a new graph equal to the dual of this graph."""
        return self.copy(dual=True)

    # def compose(self, other):
    #     """Inserts a circuit after this one. The amount of positions of the circuits must match."""
    #     if self.position_count() != other.position_count():
    #         raise TypeError("Circuits work on different position amounts")
    #     self.normalise()
    #     other = other.copy()
    #     other.normalise()
    #     for o in self.outputs:
    #         q = self.position(o)
    #         e = list(self.incident_edges(o))[0]
    #         if self.edge_type(e) == 2: #hadamard edge
    #             i = [v for v in other.inputs if other.position(v)==q][0]
    #             e = list(other.incident_edges(i))[0]
    #             other.set_edge_type(e, 3-other.edge_type(e)) # toggle the edge type
    #     d = self.depth()
    #     self.replace_subgraph(d-1,d,other)

    

    def pack_rows(self):
        """Compresses the rows of the graph so that every index is used."""
        rows = [self.row(v) for v in self.vertices()]
        new_rows = pack_indices(rows)
        for v in self.vertices():
            self.set_row(v, new_rows[self.row(v)])

    def position_count(self):
        """Returns the number of inputs of the graph"""
        return len(self.inputs)

    def auto_detect_boundary(self):
        if self.inputs or self.outputs: return self.inputs, self.outputs
        minrow = 100000
        maxrow = -100000
        nodes = {}
        ty = self.types()
        for v in self.vertices():
            if ty[v] == 0:
                r = self.row(v)
                nodes[v] = r
                if r < minrow:
                    minrow = r
                if r > maxrow:
                    maxrow = r

        for v,r in nodes.items():
            if r == minrow:
                self.inputs.append(v)
            if r == maxrow:
                self.outputs.append(v)
        self.inputs.sort(key=self.position)
        self.outputs.sort(key=self.position)
        return self.inputs, self.outputs


    # def normalise(self):
    #     """Puts every node connecting to an input/output at the correct position index and row."""
    #     if not self.inputs:
    #         self.auto_detect_boundary()
    #     max_r = self.depth() - 1
    #     if max_r <= 2: 
    #         for o in self.outputs:
    #             self.set_row(o,4)
    #         max_r = self.depth() -1
    #     claimed = []
    #     for q,i in enumerate(sorted(self.inputs, key=self.position)):
    #         self.set_row(i,0)
    #         self.set_position(i,q)
    #         #q = self.position(i)
    #         n = list(self.neighbours(i))[0]
    #         if self.type(n) in (1,2):
    #             claimed.append(n)
    #             self.set_row(n,1)
    #             self.set_position(n, q)
    #         else: #directly connected to output
    #             e = self.edge(i, n)
    #             t = self.edge_type(e)
    #             self.remove_edge(e)
    #             v = self.add_vertex(1,q,1)
    #             self.add_edge((i,v),3-t)
    #             self.add_edge((v,n), 2)
    #             claimed.append(v)
    #     for q, o in enumerate(sorted(self.outputs,key=self.position)):
    #         #q = self.position(o)
    #         self.set_row(o,max_r+1)
    #         self.set_position(o,q)
    #         n = list(self.neighbours(o))[0]
    #         if n not in claimed:
    #             self.set_row(n,max_r)
    #             self.set_position(n, q)
    #         else:
    #             e = self.edge(o, n)
    #             t = self.edge_type(e)
    #             self.remove_edge(e)
    #             v = self.add_vertex(1,q,max_r)
    #             self.add_edge((o,v),3-t)
    #             self.add_edge((v,n), 2)

    #     self.pack_rows()

    def add_vertex(self, ty=0, row=-1, position=-1):
        """Add a single vertex to the graph and return its index.
        The optional parameters allow you to respectively set
        the type, row index, and position index of the vertex."""
        v = self.add_vertices(1)[0]
        if ty: self.set_type(v, ty)
        if position!=-1: self.set_position(v, position)
        if row!=-1: self.set_row(v, row)
        return v

    def add_edge(self, source, target, data=None):
        if data != None:
            self.add_edges([(source, target)], [data])
        else:
            self.add_edges([(source, target)])
        return self._eindex - 1

    def add_arc(self, e1, e2, at_v):
        """Adds an arc between edges. e1 and e2 are the edges, at_v indicates which
        vertex to put the arc at (where -1 means both)."""

        if e2 in self._arcs[e1]:
            if at_v == self._arcs[e1][e2]: return
            else: at_v = -1
        
        self._arcs[e1][e2] = at_v
        self._arcs[e2][e1] = at_v

    def remove_arc(self, e1, e2, at_v):
        """Removes an arc between edges e1 and e2 nearest to vertex at_v, where -1 means
        both ends."""

        if e2 in self._arcs[e1]:
            if self._arcs[e1][e2] == -1 and at_v != -1:
                s,t = self.edge_st(e1)
                other_v = s if t == at_v else t
                self._arcs[e1][e2] = other_v
                self._arcs[e2][e1] = other_v
            else:
                del self._arcs[e1][e2]
                del self._arcs[e2][e1]

        

    def copy_arcs(self, e1, e2):
        """Copy the arcs from e1 on to e2. Note if there is already an arc from e1 to e2,
        this does not create a 'self-arc'."""
        for e3, at_v in self._arcs[e1].items():
            if e2 == e3: continue
            s,t = self.edge_st(e2)

            if at_v == -1:
                s1,t1 = self.edge_st(e3)
                if (s == s1 and t == t1) or (s == t1 and t == s1):
                    self.add_arc(e2, e3, -1)
            elif s == at_v or t == at_v:
                self.add_arc(e2, e3, at_v)

    def has_arc(self, e1, e2=None):
        """Return whether there is any arc between e1 and e2 (if e2 given), otherwise
        whether there are any arcs connected to e1."""
        if e2 == None:
            return len(self._arcs[e1]) != 0
        else:
            return e2 in self._arcs[e1]

    def arcs_at_v(self, v):
        for e in self.incident_edges(v):
            for e1,at_v in self._arcs[e].items():
                if e <= e1 and at_v == v: yield (e,e1)



    def signalling_nhd(self, v):
        ty = self.type(v)
        es = []
        if ty == 1 or ty == 3:
            es += [(e,self.edge_s(e)) for e in self.in_edges(v)]
        if ty == 2 or ty == 3:
            es += [(e,self.edge_t(e)) for e in self.out_edges(v)]

        nhd = []
        for i in range(len(es)):
            for j in range(i+1,len(es)):
                # ex1,ex2 = self.edata(es[i][0]), self.edata(es[j][0])
                v1,v2 = es[i][1], es[j][1]
                if self.type(v1) != 0 and self.type(v2) != 0:
                    # if ty == 3: nhd.append((v1,v2))
                    # elif not (
                    #     (ex1.negative() and ex2.negative()) or
                    #     (ex1.positive() and ex2.positive())
                    # ): nhd.append((v1,v2))
                    nhd.append((v1,v2))
        return nhd

    def roots(self):
        for v in self.vertices():
            ie = self.in_edges(v)
            if len(ie) == 1:
                v1 = self.edge_s(next(iter(ie)))
                if self.type(v1) == 0:
                    yield v
            else:
                oe = self.out_edges(v)
                if len(oe) == 1:
                    v1 = self.edge_t(next(iter(oe)))
                    if self.type(v1) == 0:
                        yield v

    def cut_edges(self, es):
        # compute shifts for parallel edges before removing anything
        stab = {e: self.edge_index(e) - (self.num_edge_siblings(e)-1)/2 for e in es}

        for e in es:
            vs, vt = self.edge_st(e)
            shift = stab[e]
            if vs > vt: shift *= -1
            v_new1 = self.add_vertex(0,
                row=(2*self.row(vs)+self.row(vt))/3.0,
                position=(2*self.position(vs)+self.position(vt))/3.0 + shift)
            v_new2 = self.add_vertex(0,
                row=(self.row(vs)+2*self.row(vt))/3.0,
                position=(self.position(vs)+2*self.position(vt))/3.0 + shift)
            
            e1 = self.add_edge(vs, v_new1)
            e2 = self.add_edge(v_new2, vt)
            self.copy_arcs(e, e1)
            self.copy_arcs(e, e2)
            self.set_edata(e1, self.edata(e))
            self.set_edata(e2, self.edata(e))
            self.remove_edge(e)

    def cut_edge(self, e):
        self.cut_edges([e])

    def cut_vertex(self, v):
        self.cut_edges([e
            for e in self.incident_edges(v)
              if self.type(self.edge_s(e)) != 0 and self.type(self.edge_t(e)) != 0])

    def decompose_vertex(self, v):
        #nhd = set()
        ty = self.type(v)
        for e in self.incident_edges(v):
            vs, vt = self.edge_st(e)
            v_other = vs if vt == v else vt
            if self.type(v_other) == 0: self.remove_vertex(v_other)
            else:
                #if (ty == 1 and vt == v) or (ty == 2 and vs == v): nhd.add(v_other)
                shift = self.edge_index(e) - (self.num_edge_siblings(e)-1)/2
                if vs > vt: shift *= -1
                v_new = self.add_vertex(0,
                    row=(self.row(v)+self.row(v_other))/2.0,
                    position=(self.position(v)+self.position(v_other))/2.0 + shift)
                if vs == v:
                    e1 = self.add_edge(v_new, vt)
                else:
                    e1 = self.add_edge(vs, v_new)
                self.copy_arcs(e, e1)
                self.set_edata(e1, self.edata(e))
        self.remove_vertex(v)
        # return nhd

    def remove_vertex(self, vertex):
        """Removes the given vertex from the graph."""
        self.remove_vertices([vertex])

    # def remove_isolated_vertices(self):
    #     """Deletes all vertices and vertex pairs that are not connected to any other vertex."""
    #     rem = []
    #     for v in self.vertices():
    #         d = self.vertex_degree(v)
    #         if d == 0:
    #             rem.append(v)
    #         if d == 1: # It has a unique neighbour
    #             if v in rem: continue # Already taken care of
    #             if self.type(v) == 0: continue # Ignore in/outputs
    #             w = list(self.neighbours(v))[0]
    #             if len(self.neighbours(w)) > 1: continue # But this neighbour has other neighbours
    #             if self.type(w) == 0: continue # It's a state/effect
    #             # At this point w and v are only connected to each other
    #             rem.append(v)
    #             rem.append(w)
    #             et = self.edge_type(self.edge(v,w))
    #     self.remove_vertices(rem)

    def vertex_set(self):
        """Returns the vertices of the graph as a Python set."""
        return set(self.vertices())

    def edge_set(self):
        """Returns the edges of the graph as a Python set."""
        return set(self.edges())

    def edge_s(self, edge):
        """Returns the source of the given edge."""
        return self._source[edge]
    def edge_t(self, edge):
        """Returns the target of the given edge."""
        return self._target[edge]

    def set_position(self, vertex, q, r):
        """Set both the position index and row index of the vertex."""
        self.set_position(vertex, q)
        self.set_row(vertex, r)

    def vindex(self): return self._vindex
    def depth(self): 
        if self._rindex: self._maxr = max(self._rindex.values())
        else: self._maxr = -1
        return self._maxr
    def position_count(self): 
        if self._pindex: self._maxp = max(self._pindex.values())
        else: self._maxp = -1
        return self._maxp + 1

    def add_vertices(self, amount, typ=0):
        for i in range(self._vindex, self._vindex + amount):
            self.graph[i] = dict()
            self.ty[i] = typ
        self._vindex += amount
        return range(self._vindex - amount, self._vindex)

    def add_edges(self, edges, data=None):
        for i in range(len(edges)):
            s,t = edges[i]
            if not t in self.graph[s]:
                self.graph[s][t] = [set(), set()]
                self.graph[t][s] = [set(), set()]
            self.graph[s][t][1].add(self._eindex)
            self.graph[t][s][0].add(self._eindex)
            self._source[self._eindex] = s
            self._target[self._eindex] = t
            self._arcs[self._eindex] = dict()
            if data != None:
                self._edata[self._eindex] = data[i]
            self._eindex += 1

        return range(self._eindex - len(edges), self._eindex)

    def remove_vertices(self, vertices):
        for v in vertices:
            # vs = list(self.graph[v])
            # remove all edges
            self.remove_edges(self.incident_edges(v))

            # for v1 in vs:
            #     del self.graph[v][v1]
            #     del self.graph[v1][v]

            # remove the vertex
            del self.graph[v]
            del self.ty[v]
            try: del self._pindex[v]
            except: pass
            try: del self._rindex[v]
            except: pass
            self._vdata.pop(v,None)

    def remove_vertex(self, vertex):
        self.remove_vertices([vertex])

    def remove_edges(self, edges):
        for e in edges:
            s,t = self.edge_st(e)
            del self._source[e]
            del self._target[e]
            for e1 in list(self._arcs[e]):
                self.remove_arc(e,e1,at_v=-1)
            del self._arcs[e]

            self.graph[s][t][1].remove(e)
            self.graph[t][s][0].remove(e)
            if len(self.graph[s][t][0]) == 0 and len(self.graph[s][t][1]) == 0:
                del self.graph[s][t]
            if len(self.graph[t][s][0]) == 0 and len(self.graph[t][s][1]) == 0:
                del self.graph[t][s]

    def remove_edge(self, edge):
        self.remove_edges([edge])

    def num_vertices(self):
        return len(self.graph)

    def num_edges(self):
        return len(self._source)

    def num_arcs(self):
        return self._num_arcs

    def vertices(self):
        return self.graph.keys()

    def vertices_in_range(self, start, end):
        """Returns all vertices with index between start and end
        that only have neighbours whose indices are between start and end"""
        for v in self.graph.keys():
            if not start<v<end: continue
            if all(start<v2<end for v2 in self.graph[v]):
                yield v

    def edges(self):
        return self._source.keys()

    def arcs(self):
        ar = []
        for e1 in self.edges():
            for e2, a in self._arcs[e1].items():
                if e1 <= e2:
                    if a == -1:
                        s,t = self.edge_st(e1)
                        ar.append((e1,e2,s))
                        ar.append((e1,e2,t))
                    else:
                        ar.append((e1,e2,a))

        return ar

    # def edges_in_range(self, start, end, safe=False):
    #     """like self.edges, but only returns edges that belong to vertices 
    #     that are only directly connected to other vertices with 
    #     index between start and end.
    #     If safe=True then it also checks that every neighbour is only connected to vertices with the right index"""
    #     if not safe:
    #         for v0,adj in self.graph.items():
    #             if not (start<v0<end): continue
    #             #verify that all neighbours are in range
    #             if all(start<v1<end for v1 in adj):
    #                 for v1 in adj:
    #                     if v1 > v0: yield (v0,v1)
    #     else:
    #         for v0,adj in self.graph.items():
    #             if not (start<v0<end): continue
    #             #verify that all neighbours are in range, and that each neighbour
    #             # is only connected to vertices that are also in range
    #             if all(start<v1<end for v1 in adj) and all(all(start<v2<end for v2 in self.graph[v1]) for v1 in adj):
    #                 for v1 in adj:
    #                     if v1 > v0:
    #                         yield (v0,v1)
    
    def edge_st(self, edge):
        return (self._source[edge], self._target[edge])

    def edge_index(self, edge):
        s,t = self.edge_st(edge)
        return (sum(1 for e1 in self.graph[s][t][0] if e1 < edge) +
                sum(1 for e1 in self.graph[s][t][1] if e1 < edge))

    def num_edge_siblings(self, edge):
        s,t = self.edge_st(edge)
        return len(self.graph[s][t][0]) + len(self.graph[s][t][1])


    def neighbours(self, vertex):
        return self.graph[vertex].keys()

    def vertex_degree(self, vertex):
        return len(self.in_edges(vertex)) + len(self.out_edges(vertex))

    def in_edges(self, v):
        es = set()
        for (w, (ie,oe)) in self.graph[v].items():
            es.update(ie)
        return es

    def out_edges(self, v):
        es = set()
        for (w, (ie,oe)) in self.graph[v].items():
            es.update(oe)
        return es

    def incident_edges(self, v):
        es = set()
        for (w, (ie,oe)) in self.graph[v].items():
            es.update(ie)
            es.update(oe)
        return es

    def connected(self,v1,v2):
        return v2 in self.graph[v1]

    # def edge_type(self, e):
    #     v1,v2 = e
    #     try:
    #         return self.graph[v1][v2]
    #     except KeyError:
    #         return 0

    def type(self, vertex):
        return self.ty[vertex]
    def types(self):
        return self.ty
    def set_type(self, vertex, t):
        self.ty[vertex] = t

    def position(self, vertex):
        return self._pindex.get(vertex,-1)
    def positions(self):
        return self._pindex
    def set_position(self, vertex, q):
        if q > self._maxp: self._maxp = q
        self._pindex[vertex] = q

    def row(self, vertex):
        return self._rindex.get(vertex, -1)
    def rows(self):
        return self._rindex
    def set_row(self, vertex, r):
        if r > self._maxr: self._maxr = r
        self._rindex[vertex] = r

    def vdata(self, vertex, default=None):
        if vertex in self._vdata:
            return self._vdata[vertex]
        else:
            return default

    def set_vdata(self, vertex, val):
        if vertex in self._vdata:
            self._vdata[vertex] = val
        else:
            self._vdata[vertex] = val

    def edata(self, edge, default=None):
        if edge in self._edata:
            return self._edata[edge]
        else:
            return default

    def set_edata(self, edge, val):
        if edge in self._edata:
            self._edata[edge] = val
        else:
            self._edata[edge] = val

    def dfs(self, v, visited, visit=None, parent=None):
        if visit != None: visit(v)
        if not v in visited:
            visited.add(v)
            # traverse using edges to detect parallel & self-loops
            for e in self.incident_edges(v):
                s,t = self.edge_st(e)
                v1 = s if s != v else t
                if v1 == parent: continue
                self.dfs(v1, visited, visit, parent=v)


    def component(self, v):
        comp = set()
        self.dfs(v, comp)
        return comp

    def connected(self, v1, v2):
        def find(v):
            if v == v2: raise Exception("found")
            return True
        try: self.dfs(v1, set(), find)
        except Exception: return True
        return False


    def is_acyclic(self, from_v=None):
        verts = set([from_v]) if from_v != None else set(self.vertices())
        visited = set()

        def check(v):
            if v in visited: raise Exception("cycle")
            verts.discard(v)

        try:
            while len(verts) > 0:
                self.dfs(next(iter(verts)), visited, check)
        except Exception:
            return False
        
        return True

    def remove_acyclic(self):
        verts = set(self.vertices())
        while len(verts) > 0:
            v = next(iter(verts))
            comp = self.component(v)
            verts -= comp
            if self.is_acyclic(from_v=v):
                self.remove_vertices(comp)



    def fuse_edges(self, e1, e2):
        self.copy_arcs(e1, e2)
        self.remove_edge(e1)

    def contract_edge(self, edge):
        v1,v2 = self.edge_st(edge)
        ine = self.in_edges(v1)
        oute = self.out_edges(v1)
        v2e = self.incident_edges(v2)

        # TODO: do something better w self-loops?
        etab = dict()
        for e in ine:
            if e == edge: continue
            etab[e] = self.add_edge(self.edge_s(e), v2, self.edata(e))

        for e in oute:
            if e == edge: continue
            if e in etab: raise ValueError("self-loop in fusion")
            etab[e] = self.add_edge(v2, self.edge_t(e), self.edata(e))

        for e1,e2,end in self.arcs():
            at_v = self.edge_s(min(e1,e2)) if end == 0 else self.edge_t(min(e1,e2))
            new_v = v2 if at_v == v1 else at_v

            if e1 == edge or e2 == edge:
                e1p = e1 if e2 == edge else e2
                if e1p in etab:
                    for e2p in v2e:
                        s,t = self.edge_st(min(etab[e1p],e2p))
                        self.add_arc(etab[e1p], e2p, end=0 if new_v == s else 1)
                elif e1p in v2e:
                    for e2p in etab:
                        s,t = self.edge_st(min(e1p,etab[e2p]))
                        self.add_arc(e1p, etab[e2p], end=0 if new_v == s else 1)

            else:
                e1p = etab[e1] if e1 in etab else e1
                e2p = etab[e2] if e2 in etab else e2
                
                if e1p != e1 or e2p != e2:
                    s,t = self.edge_st(min(e1p,e2p))
                    self.add_arc(e1p, e2p, end=0 if new_v == s else 1)

        self.remove_vertex(v1)

    def contract1(self, safe=True):
        for e1,e2,end in self.arcs():
            if self.edge_s(e1) == self.edge_s(e2) and self.edge_t(e1) == self.edge_t(e2):
                self.fuse_edges(e1, e2)
                return True
        for e in self.edges():
            if safe and self.has_arc(e): continue
            s,t = self.edge_st(e)
            if self.type(s) == 0 or self.type(t) == 0:
                continue
            if len(self.graph[s][t][0]) + len(self.graph[s][t][1]) == 1:
                self.contract_edge(e)
                # self.fuse_vertices(s,t)
                return True
        return False

    def is_point(self):
        return sum(1 for v in self.vertices() if self.type(v) != 0) == 1


