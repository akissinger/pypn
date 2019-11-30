define(['d3'], function(d3) {
    
    // styling functions
    function nodeColor(t) {
        if (t == 0) return "black";
        else if (t == 1) return "blue";
        else if (t == 2) return "red";
        else if (t == 3) return "yellow";
    }

    function edgeColor(t) {
        if (t == 1) return "black";
        else if (t == 2) return "#08f";
    }

    function nodeStyle(selected) {
        return selected ? "stroke-width: 2px; stroke: #00f" : "stroke-width: 1.5px";
    }

    return {
    showGraph: function(tag, graph, width, height, scale, node_size, show_labels) {
        var ntab = {};

        graph.nodes.forEach(function(d) {
            ntab[d.name] = d;
            d.selected = false;
            d.previouslySelected = false;
            d.nhd = [];
        });

        var spiders_and_boundaries = graph.nodes.filter(function(d) {
            return d.t != 3;
        });

        graph.links.forEach(function(d) {
            var s = ntab[d.source];
            var t = ntab[d.target];
            d.source = s;
            d.target = t;
            s.nhd.push(t);
            t.nhd.push(s);
        });

        var shiftKey;

        // SETUP SVG ITEMS

        var svg = d3.select(tag)
            //.attr("tabindex", 1)
            .on("keydown.brush", function() {shiftKey = d3.event.shiftKey || d3.event.metaKey;})
            .on("keyup.brush", function() {shiftKey = d3.event.shiftKey || d3.event.metaKey;})
            //.each(function() { this.focus(); })
            .append("svg")
            .attr("style", "max-width: none; max-height: none")
            .attr("width", width)
            .attr("height", height);

        svg.append('defs')
            // .selectAll('marker')
            //   .data(['end'])
            //   .enter()
            .append('marker')
              .attr('id', "arrowhead")
              .attr('viewBox', '0 -5 10 10')
              .attr('refX', node_size * 3)
              .attr('refY', 0)
              .attr('orient', 'auto')
              .attr('markerWidth', 5)
              .attr('markerHeight', 5)
              .attr('markerUnits', "strokeWidth")
              .attr('xoverflow','visible')
              .append('path')
              .attr('d', 'M0,-5L10,0L0,5')
              .attr('fill', '#000');

        function path_data(d) {
            var s = "M " + d.source.x + " " + d.source.y;

            var edge_index = (d.flip_orientation) ?
                d.num_edge_siblings - d.edge_index - 1 : d.edge_index;

            var center_index = (d.num_edge_siblings-1)/2;

            if (d.num_edge_siblings == 1 || edge_index == center_index) {
                s += " L " + d.target.x + " " + d.target.y;
            } else {
                var dx = d.target.x - d.source.x;
                var dy = d.target.y - d.source.y;
                var dist = Math.sqrt(dx * dx + dy * dy);
                var rx = 1.1 * (dist / 2);
                var ry = Math.abs(edge_index - center_index) * 1.5 * scale;//3.0 * (dist / 2);
                var rotate_x = Math.atan2(dy,dx) * (180/Math.PI);

                var bend_right;
                if (edge_index < d.num_edge_siblings/2) {
                    bend_right = false;
                } else {
                    bend_right = true;
                }

                // always take the short arc, then choose direction based on edge index
                var which_arc = bend_right ? "0 1" : "0 0";
                s += " A " + rx + " " + ry + " " + rotate_x + " " + which_arc + " " + d.target.x + " " + d.target.y;
            }

            return s;
        }

        // var link = svg.append("g")
        //     .attr("class", "link")
        //     .selectAll("line")
        //     .data(graph.links)
        //     .enter().append("line")
        //     .attr("stroke", "black")
        //     .attr("style", "stroke-width: 1.5px");
        var link = svg.append("g")
            .attr("class", "link")
            .selectAll("path")
            .data(graph.links)
            .enter().append("path")
            .attr("stroke", "black")
            .attr("fill", "none")
            .attr("style", "stroke-width: 1.5px")
            .attr('marker-end','url(#arrowhead)');

        var brush = svg.append("g")
            .attr("class", "brush");

        var node = svg.append("g")
            .attr("class", "node")
            .selectAll("g")
            .data(graph.nodes)
            .enter().append("g")
            .attr("transform", function(d) {
                return "translate(" + d.x + "," + d.y +")";
            });

        node.filter(function(d) { return d.t != 3; })
            .append("circle")
            .attr("r", node_size)
            .attr("fill", function(d) { return nodeColor(d.t); })
            .attr("stroke", "black");

        // node.filter(function(d) { return d.phase != ''; })
        //     .append("text")
        //     .attr("y", 0.7 * node_size + 14)
        //     .text(function (d) { return d.phase })
        //     .attr("text-anchor", "middle")
        //     .attr("font-size", "12px")
        //     .attr("font-family", "monospace")
        //     .attr("fill", "#00d");

        if (show_labels) {
            node.append("text")
                .attr("y", -0.7 * node_size - 5)
                .text(function (d) { return d.name; })
                .attr("text-anchor", "middle")
                .attr("font-size", "8px")
                .attr("font-family", "monospace")
                .attr("fill", "#ccc");
        }

        // link.attr("x1", function(d) { return d.source.x; })
        //     .attr("y1", function(d) { return d.source.y; })
        //     .attr("x2", function(d) { return d.target.x; })
        //     .attr("y2", function(d) { return d.target.y; });
        link.attr("d", path_data);

        // EVENTS FOR DRAGGING AND SELECTION

        node.on("mousedown", function(d) {
                if (shiftKey) {
                    d3.select(this).select(":first-child").attr("style", nodeStyle(d.selected = !d.selected));
                    d3.event.stopImmediatePropagation();
                } else if (!d.selected) {
                    node.select(":first-child").attr("style", function(p) { return nodeStyle(p.selected = d === p); });
                }
            })
            .call(d3.drag().on("drag", function(d) {
                var dx = d3.event.dx;
                var dy = d3.event.dy;
                // node.filter(function(d) { return d.selected; })
                //     .attr("cx", function(d) { return d.x += dx; })
                //     .attr("cy", function(d) { return d.y += dy; });
                node.filter(function(d) { return d.selected; })
                    .attr("transform", function(d) {
                        d.x += dx;
                        d.y += dy;
                        return "translate(" + d.x + "," + d.y +")";
                    });

                link.filter(function(d) { return d.source.selected || d.target.selected; })
                    .attr("d", path_data);
                    

                // link.filter(function(d) { return d.target.selected; })
                //     .attr("x2", function(d) { return d.target.x; })
                //     .attr("y2", function(d) { return d.target.y; });

                // text.filter(function(d) { return d.selected; })
                //     .attr("x", function(d) { return d.x; })
                //     .attr("y", function(d) { return d.y + 0.7 * node_size + 14; });
            }));

        brush.call(d3.brush()
            .extent([[0, 0], [width, height]])
            .on("start", function() {
                if (d3.event.sourceEvent.type !== "end") {
                    node.select(":first-child").attr("style", function(d) {
                        return nodeStyle(
                            d.selected = d.previouslySelected = shiftKey &&
                            d.selected);
                    });
                }
            })
            .on("brush", function() {
                if (d3.event.sourceEvent.type !== "end") {
                    var selection = d3.event.selection;
                    node.select(":first-child").attr("style", function(d) {
                        return nodeStyle(d.selected = d.previouslySelected ^
                            (selection != null
                            && selection[0][0] <= d.x && d.x < selection[1][0]
                            && selection[0][1] <= d.y && d.y < selection[1][1]));
                    });
                }
            })
            .on("end", function() {
                if (d3.event.selection != null) {
                    d3.select(this).call(d3.event.target.move, null);
                }
            }));
    }};
});
