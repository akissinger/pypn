
def decompose(e, g, row=0):
    v = g.add_vertex(row=row)
    pos = knuth_tree_layout(e, g, row+1, 0, v)
    g.set_position(v, pos / 2)

def knuth_tree_layout(e, g, row, min_pos, parent_v):
    v = g.add_vertex(row=row)
    g.add_edge(parent_v, v, data = e)

    pos = min_pos
    if e.children() != None:
        for c in e.children():
            pos = knuth_tree_layout(c, g, row+1, pos, v) + 1
        pos -= 1

    g.set_position(v, (min_pos + pos) / 2)
    return pos


# i = 0
# def knuth_layout(tree, depth):
#     if tree.left_child: 
#         knuth_layout(tree.left_child, depth+1)
#     tree.x = i
#     tree.y = depth
#     i += 1
#     if tree.right_child: 
#         knuth_layout(tree.right_child, depth+1)