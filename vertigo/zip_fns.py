import itertools

from graph import GraphNode, plain_copy

def key_funcs():
    '''Namespace for key selection functions.'''

    def _non_none(graphs):
        return [n for n in graphs if n is not None]

    def union(graphs):
        '''Iterate over all keys of all graphs, skipping duplicates.'''
        keys = itertools.chain(*[g.key_iter() for g in _non_none(graphs)])
        used = set()
        for key in keys:
            if key not in used:
                used.add(key)
                yield key

    def intersection(graphs):
        '''Iterate over only keys that are in all graphs.'''
        graphs = _non_none(graphs)
        if not graphs:
            return
        for key in union(graphs):
            for graph in graphs:
                if key not in graph:
                    break
            else:
                yield key

    def first(graphs):
        '''Iterate over the first graph's keys and no others.'''
        if graphs and graphs[0]:
            for key in graphs[0].key_iter():
                yield key

    def get_key_fn(name):
        key_fns = dict(
            union=union,
            intersection=intersection,
            first=first,
        )
        return key_fns[name]
    return get_key_fn

get_key_fn = key_funcs()


class ZippedGraphNode(GraphNode):
    '''GraphNode that zips other nodes together.

    When you zip N graphs together, the value of a given node will be an N-tuple
    of (v_1, v_2, ..., v_N), where v_n is the value of the corresponding node in
    the nth graph, or None if that graph has no such node.

    The argument merge_fn determines what nodes will appear in the zipped graph.
    You can pass in a function that takes a set of graphs and returns an
    iterable of keys, or you can pass in one of the following strings to use a
    predefined merge function:

    'intersection' - the new graph has only those edges that were present in all
        input graphs. This is the default.

    'union' - the new graph has all edges present in any input graphs.

    'first' - the new graph has the same structure as the first input graph.
    '''
    def __init__(self, graphs, merge_fn='intersection'):
        self.graphs = tuple(graphs)
        if isinstance(merge_fn, basestring):
            merge_fn = get_key_fn(merge_fn)
        self.merge_fn = merge_fn

    @property
    def value(self):
        return tuple(g.value if g else None for g in self.graphs)

    def key_iter(self):
        return self.merge_fn(self.graphs)

    def _get_child(self, key):
        graphs = [(n.get_child(key, None) if n else None) for n in self.graphs]
        return ZippedGraphNode(graphs, merge_fn=self.merge_fn)


def izip(*graphs, **kwargs):
    '''Return a ZippedGraphNode wrapping the input graphs.

    The only allowable kwarg is merge_fn; see the docs for ZippedGraphNode.
    '''
    merge_fn = kwargs.pop('merge_fn', 'intersection')
    return ZippedGraphNode(graphs, merge_fn=merge_fn)


def zip(*graphs, **kwargs):
    '''Zip several graphs together, returning a new graph.

    Unlike izip, which returns a ZippedGraphNode that generates its children as
    requested, zip returns a graph made of PlainGraphNodes. It's just plain_copy
    composed with izip:

    zip(*graphs) == plain_copy(izip(*graphs))

    '''
    return plain_copy(izip(*graphs, **kwargs))


def test_zip():
    from graph import ObjectGraphNode, PlainGraphNode
    from walker import top_down
    from collections import OrderedDict as d
    tree1 = PlainGraphNode.build(d([
        ('_self', 'Root'),
        ('a', d([
            ('_self', 'Value A'),
            ('a-1', 'Value A-1'),
        ])),
        ('b', 'Value B')
    ]))
    tree2 = PlainGraphNode.build(d([
        ('_self', "Root'"),
        ('a', "Value A'"),
        ('c', "Value C'"),
    ]))


    union = PlainGraphNode.build(d([
        ('_self', ("Root", "Root'")),
        ('a', d([
            ('_self', ("Value A", "Value A'")),
            ('a-1', ("Value A-1", None)),
        ])),
        ('b', ("Value B", None),),
        ('c', (None, "Value C'"),),
    ]))

    intersection = union.subgraph({'a':[]})

    first = union.subgraph(['a', 'b'])

    assert izip(tree1, tree2, merge_fn='union').all_equals(union)
    assert izip(tree1, tree2, merge_fn='intersection').all_equals(intersection)
    assert izip(tree1, tree2, merge_fn='first').all_equals(first)

    assert zip(tree1, tree2).all_equals(izip(tree1, tree2))

if __name__ == '__main__':
    test_zip()