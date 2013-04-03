var FuncNode = Class.$extend({
    __init__ : function(key, stats) {
        this.key = key;
        this.calls = stats[0];
        this.recursive = stats[1];
        this.local = stats[2];
        this.cumulative = stats[3];
        this.callers = stats[4];

        this.children = [];
        this.parents = [];
    },

    weave : function(nodes) {
        var parent;

        for (var caller in this.callers) {
            if (nodes.hasOwnProperty(caller)) {
                parent = nodes[caller];
                this.parents.push(parent);
                parent.children.push(this);
            }
        }
    }
});

var stats_to_tree = function stats_to_tree(json) {
    var node;
    var root = null;
    var nodes = {};

    // load lines from stats dict into nodes
    for (var k in json) {
        if (json.hasOwnProperty(k)) {
            nodes[k] = FuncNode(k, json[k]);
        }
    }

    // connect children and parents
    for (var k in nodes) {
        if (nodes.hasOwnProperty(k)) {
            nodes[k].weave(nodes);
        }
    }

    // choose a root node
    for (var k in nodes) {
        if (nodes.hasOwnProperty(k)) {
            node = nodes[k];

            // node has no parents: one requirement for root
            if (node.parents.length === 0) {
                // node has called something else: second requirement for root
                for (var kk in nodes) {
                    if (nodes[kk].callers.hasOwnProperty(k)) {
                        root = node;
                    }
                }
            }
        }
    }

    return root;
};
