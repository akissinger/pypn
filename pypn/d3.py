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

import json
import random
from fractions import Fraction

__all__ = ['init', 'draw']

try:
    from IPython.display import display, HTML
    in_notebook = True
    javascript_location = '../js'
except ImportError:
    in_notebook = False
    javascript_location = '/js'
    try:
        from browser import document, html
        in_webpage = True
    except ImportError:
        in_webpage = False

# Provides functions for displaying hocc graphs in jupyter notebooks using d3

#_d3_display_seq = 0

# javascript_location = '../js'


def draw(g, scale=None, row_scale=1, labels=False):
    #global _d3_display_seq
    if not g:
        print("FAIL")
        return

    if not in_notebook and not in_webpage: 
        raise Exception("This method only works when loaded in a webpage or Jupyter notebook")

    if not hasattr(g, 'vertices'):
        g = g.to_graph(zh=True)

    #_d3_display_seq += 1

    # generate a 'unique' id for this graph
    seq = random.randint(0,1000000000) #_d3_display_seq

    if scale == None:
        scale = 50
        # scale = 800 / (g.depth() + 2)
        # if scale > 50: scale = 50
        # if scale < 20: scale = 20

    node_size = 0.1 * scale
    if node_size < 2: node_size = 2

    w = (g.depth() + 2) * scale * row_scale
    h = (g.position_count() + 3) * scale

    nodes = [{'name': str(v),
              'x': (g.row(v) + 1) * scale * row_scale,
              'y': (g.position(v) + 2) * scale,
              't': g.type(v) }
             for v in g.vertices()]
    links = [{'id': str(e),
              'label': str(g.edata(e, default='')),
              'source': str(g.edge_s(e)),
              'target': str(g.edge_t(e)),
              'edge_index': g.edge_index(e),
              'num_edge_siblings': g.num_edge_siblings(e),
              'flip_orientation': g.edge_s(e) > g.edge_t(e) } for e in g.edges()]
    arcs = [{'source': str(e1),
             'target': str(e2),
             'at_v': str(at_v)} for e1,e2,at_v in g.arcs()]
    graphj = json.dumps({'nodes': nodes, 'links': links, 'arcs': arcs})
    text = """
        <div style="overflow:auto" id="graph-output-{0}"></div>
        <script type="text/javascript">
        require.config({{ baseUrl: "{1}",
                         paths: {{d3: "d3.v4.min"}} }});
        require(['hocc'], function(hocc) {{
            hocc.showGraph('{0}', '#graph-output-{0}',
            JSON.parse('{2}'), {3}, {4}, {5}, {6}, {7});
        }});
        </script>
        """.format(seq, javascript_location, graphj, w, h, scale, node_size,
            'true' if labels else 'false')
    
    display(HTML(text))
    
