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
        self._vindex = 0
        self.nedges = 0
        self.ty = dict()
        self._pindex = dict()
        self._maxp = -1
        self._rindex = dict()
        self._maxr = -1
        
        self._vdata = dict()
        self._edata = dict()

    def __str__(self):
        return "Graph({} vertices, {} edges)".format(
                str(self.num_vertices()),str(self.num_edges()))

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
        qs = self.positions()
        rs = self.rows()
        maxr = self.depth()
        vtab = dict()
        for v in self.vertices():
            i = g.add_vertex(ty[v])
            if v in qs: g.set_position(i,qs[v])
            if v in rs: 
                if dual: g.set_row(i, maxr-rs[v])
                else: g.set_row(i, rs[v])
            vtab[v] = i
            for k in self.vdata_keys(v):
                g.set_vdata(i, k, self.vdata(v, k))

        for i in self.inputs:
            if dual: g.outputs.append(vtab[i])
            else: g.inputs.append(vtab[i])
        for o in self.outputs:
            if dual: g.inputs.append(vtab[o])
            else: g.outputs.append(vtab[o])
        
        etab = {e:(vtab[self.edge_s(e)],vtab[self.edge_t(e)]) for e in self.edges()}
        g.add_edges(etab.values())
        for e,(s,t) in etab.items():
            g.set_edge_type(g.edge(s,t), self.edge_type(e))
        return g

    def dual(self):
        """Returns a new graph equal to the dual of this graph."""
        return self.copy(dual=True)

    def compose(self, other):
        """Inserts a circuit after this one. The amount of positions of the circuits must match."""
        if self.position_count() != other.position_count():
            raise TypeError("Circuits work on different position amounts")
        self.normalise()
        other = other.copy()
        other.normalise()
        for o in self.outputs:
            q = self.position(o)
            e = list(self.incident_edges(o))[0]
            if self.edge_type(e) == 2: #hadamard edge
                i = [v for v in other.inputs if other.position(v)==q][0]
                e = list(other.incident_edges(i))[0]
                other.set_edge_type(e, 3-other.edge_type(e)) # toggle the edge type
        d = self.depth()
        self.replace_subgraph(d-1,d,other)

    

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


    def normalise(self):
        """Puts every node connecting to an input/output at the correct position index and row."""
        if not self.inputs:
            self.auto_detect_boundary()
        max_r = self.depth() - 1
        if max_r <= 2: 
            for o in self.outputs:
                self.set_row(o,4)
            max_r = self.depth() -1
        claimed = []
        for q,i in enumerate(sorted(self.inputs, key=self.position)):
            self.set_row(i,0)
            self.set_position(i,q)
            #q = self.position(i)
            n = list(self.neighbours(i))[0]
            if self.type(n) in (1,2):
                claimed.append(n)
                self.set_row(n,1)
                self.set_position(n, q)
            else: #directly connected to output
                e = self.edge(i, n)
                t = self.edge_type(e)
                self.remove_edge(e)
                v = self.add_vertex(1,q,1)
                self.add_edge((i,v),3-t)
                self.add_edge((v,n), 2)
                claimed.append(v)
        for q, o in enumerate(sorted(self.outputs,key=self.position)):
            #q = self.position(o)
            self.set_row(o,max_r+1)
            self.set_position(o,q)
            n = list(self.neighbours(o))[0]
            if n not in claimed:
                self.set_row(n,max_r)
                self.set_position(n, q)
            else:
                e = self.edge(o, n)
                t = self.edge_type(e)
                self.remove_edge(e)
                v = self.add_vertex(1,q,max_r)
                self.add_edge((o,v),3-t)
                self.add_edge((v,n), 2)

        self.pack_rows()

    def add_vertex(self, ty=0, row=-1, position=-1):
        """Add a single vertex to the graph and return its index.
        The optional parameters allow you to respectively set
        the type, row index, and position index of the vertex."""
        v = self.add_vertices(1)[0]
        if ty: self.set_type(v, ty)
        if position!=-1: self.set_position(v, position)
        if row!=-1: self.set_row(v, row)
        return v

    def add_edge(self, edge, edgetype=1):
        """Adds a single edge of the given type (1=regular, 2=Hadamard edge)"""
        self.add_edges([edge], edgetype)

    def remove_vertex(self, vertex):
        """Removes the given vertex from the graph."""
        self.remove_vertices([vertex])

    def remove_isolated_vertices(self):
        """Deletes all vertices and vertex pairs that are not connected to any other vertex."""
        rem = []
        for v in self.vertices():
            d = self.vertex_degree(v)
            if d == 0:
                rem.append(v)
            if d == 1: # It has a unique neighbour
                if v in rem: continue # Already taken care of
                if self.type(v) == 0: continue # Ignore in/outputs
                w = list(self.neighbours(v))[0]
                if len(self.neighbours(w)) > 1: continue # But this neighbour has other neighbours
                if self.type(w) == 0: continue # It's a state/effect
                # At this point w and v are only connected to each other
                rem.append(v)
                rem.append(w)
                et = self.edge_type(self.edge(v,w))
        self.remove_vertices(rem)

    def remove_edge(self, edge):
        """Removes the given edge from the graph."""
        self.remove_edge([edge])

    def vertex_set(self):
        """Returns the vertices of the graph as a Python set. 
        Should be overloaded if the backend supplies a cheaper version than this."""
        return set(self.vertices())

    def edge_set(self):
        """Returns the edges of the graph as a Python set. 
        Should be overloaded if the backend supplies a cheaper version than this."""
        return set(self.edges())

    def edge_s(self, edge):
        """Returns the source of the given edge."""
        return self.edge_st(edge)[0]
    def edge_t(self, edge):
        """Returns the target of the given edge."""
        return self.edge_st(edge)[1]

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

    def add_vertices(self, amount):
        for i in range(self._vindex, self._vindex + amount):
            self.graph[i] = dict()
            self.ty[i] = 0
        self._vindex += amount
        return range(self._vindex - amount, self._vindex)

    def add_edges(self, edges, edgetype=1):
        for s,t in edges:
            self.nedges += 1
            self.graph[s][t] = edgetype
            self.graph[t][s] = edgetype

    def remove_vertices(self, vertices):
        for v in vertices:
            vs = list(self.graph[v])
            # remove all edges
            for v1 in vs:
                self.nedges -= 1
                del self.graph[v][v1]
                del self.graph[v1][v]
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
        for s,t in edges:
            self.nedges -= 1
            del self.graph[s][t]
            del self.graph[t][s]

    def remove_edge(self, edge):
        self.remove_edges([edge])

    def num_vertices(self):
        return len(self.graph)

    def num_edges(self):
        return self.nedges

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
        for v0,adj in self.graph.items():
            for v1 in adj:
                if v1 > v0: yield (v0,v1)

    def edges_in_range(self, start, end, safe=False):
        """like self.edges, but only returns edges that belong to vertices 
        that are only directly connected to other vertices with 
        index between start and end.
        If safe=True then it also checks that every neighbour is only connected to vertices with the right index"""
        if not safe:
            for v0,adj in self.graph.items():
                if not (start<v0<end): continue
                #verify that all neighbours are in range
                if all(start<v1<end for v1 in adj):
                    for v1 in adj:
                        if v1 > v0: yield (v0,v1)
        else:
            for v0,adj in self.graph.items():
                if not (start<v0<end): continue
                #verify that all neighbours are in range, and that each neighbour
                # is only connected to vertices that are also in range
                if all(start<v1<end for v1 in adj) and all(all(start<v2<end for v2 in self.graph[v1]) for v1 in adj):
                    for v1 in adj:
                        if v1 > v0:
                            yield (v0,v1)

    def edge(self, s, t):
        return (s,t) if s < t else (t,s)
    def edge_set(self):
        return set(self.edges())
    def edge_st(self, edge):
        return edge

    def neighbours(self, vertex):
        return self.graph[vertex].keys()

    def vertex_degree(self, vertex):
        return len(self.graph[vertex])

    def incident_edges(self, vertex):
        return [(vertex, v1) if v1 > vertex else (v1, vertex) for v1 in self.graph[vertex]]

    def connected(self,v1,v2):
        return v2 in self.graph[v1]

    def edge_type(self, e):
        v1,v2 = e
        try:
            return self.graph[v1][v2]
        except KeyError:
            return 0

    def set_edge_type(self, e, t):
        v1,v2 = e
        self.graph[v1][v2] = t
        self.graph[v2][v1] = t

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

    def vdata_keys(self, vertex):
        return self._vdata.get(vertex, {}).keys()
    def vdata(self, vertex, key, default=0):
        if vertex in self._vdata:
            return self._vdata[vertex].get(key,default)
        else:
            return default
    def set_vdata(self, vertex, key, val):
        if vertex in self._vdata:
            self._vdata[vertex][key] = val
        else:
            self._vdata[vertex] = {key:val}
