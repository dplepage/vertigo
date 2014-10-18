import itertools
from collections import OrderedDict
import sys

if sys.version < '3': # pragma: no cover
    text_type = unicode
else: # pragma: no cover
    text_type = str
    basestring = str

from .graph import GraphNode, plain_copy, PlainGraphNode
from .walker import bottom_up

class StructureMismatch(Exception):
    pass

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

def last(graphs):
    '''Iterate over the last graph's keys and no others.'''
    if graphs and graphs[-1]:
        for key in graphs[-1].key_iter():
            print(key)
            yield key

def strict(graphs):
    '''Raise StructureMismatch unless all graphs have the same keys.'''
    return list(_strict(graphs))

def _strict(graphs):
    for key in union(graphs):
        for graph in graphs:
            if key not in graph:
                raise StructureMismatch(key)
        else:
            yield key

def get_key_fn(name):
    # if name == 'strict':
    #     raise Exception('get_key_fn')
    key_fns = dict(
        union=union,
        intersection=intersection,
        first=first,
        last=last,
        strict=strict,
    )
    return key_fns[name]

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

    'strict' - a StructureMismatch() will be raised unless all graphs have the
            same set of edges.

    The argument default determines what value will appear at nodes where some
    graphs don't exist. For example, if the merge_fn is union and the first
    graph has g1['foo'].value == 1, but second graph doesn't contain the edge
    'foo', then the value at 'foo' in the zipped graph will be (1, <default>)

    default defaults to None; you can pass in a placeholder such as Missing to
    distinguish between nodes where a graph exists but has value None and nodes
    where that graph doesn't exist.

    '''
    def __init__(self, graphs, merge_fn='intersection', default=None):
        self.graphs = tuple(graphs)
        if isinstance(merge_fn, basestring):
            merge_fn = get_key_fn(merge_fn)
        self.default = default
        self.merge_fn = merge_fn

    def _build_child(self, graphs):
        return type(self)(graphs, merge_fn=self.merge_fn, default=self.default)

    @property
    def value(self):
        return tuple(g.value if g else self.default for g in self.graphs)

    def key_iter(self):
        return self.merge_fn(self.graphs)

    def _get_child(self, key):
        graphs = [(n.get_child(key, None) if n else None) for n in self.graphs]
        return self._build_child(graphs)


def izip(*graphs, **kwargs):
    '''Return a ZippedGraphNode wrapping the input graphs.

    The only allowable kwargs are merge_fn and default; see the docs for
    ZippedGraphNode.
    '''
    merge_fn = kwargs.pop('merge_fn', 'intersection')
    default = kwargs.pop('default', None)
    return ZippedGraphNode(graphs, merge_fn=merge_fn, default=default)


def zip(*graphs, **kwargs):
    '''Zip several graphs together, returning a new graph.

    Unlike izip, which returns a ZippedGraphNode that generates its children as
    requested, zip returns a graph made of PlainGraphNodes. It's just plain_copy
    composed with izip:

    zip(*graphs) == plain_copy(izip(*graphs))

    '''
    cls = kwargs.pop('cls', PlainGraphNode)
    return plain_copy(izip(*graphs, **kwargs), cls)


@bottom_up
def unzip(values, _path, children, _pre, cls=PlainGraphNode):
    '''Unzip a zipped graph node.

    The input graph should be a zipped graph, that is, a graph whose values are
    all tuples of the same length. The returned value will be a tuple of graphs,
    each of which has one slice of the values. This is, broadly, the opposite of
    zip, in that unzip(zip(*graphs, merge_fn='strict')) will return a tuple
    equivalent to graphs if all the graphs have the same structure.

    For other merge_fns, zip may drop nodes or add empty nodes, so they will not
    be perfect opposites.
    '''
    trees = []
    for i in range(len(values)):
        kids = OrderedDict()
        for key in children:
            kids[key] = children[key][i]
        trees.append(cls(values[i], kids))
    return tuple(trees)

