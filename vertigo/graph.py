from abc import ABCMeta, abstractmethod
from collections import OrderedDict


class Missing(object):
    # singleton placeholder for missing values
    pass
Missing = Missing()


class Graphable(object):
    '''Base class for all directed graph structures.

    These structures consist of nodes, each of which has a set of uniquely-
    labeled outgoing edges to other nodes.

    This interface describes the bare minimum needed to describe such a
    structure: the ability to list the keys of the outgoing edges, and the
    ability to follow an edge by key. Subclasses should implement key_iter()
    for the first, and _get_child(key) for the second.

    Most actual graph manipulation happens via subclasses of the GraphNode type
    below. The main advantage to inheriting from Graphable instead of GraphNode
    is that your type will not carry all the graph manipulation functions with
    it. The main disadvantage is that you will need to wrap your Graphable in
    a GraphableGraphNode in order to do graph operations on it.

    '''
    __metaclass__ = ABCMeta
    __slots__ = ()

    @abstractmethod
    def key_iter(self):
        '''Iterate over the edge keys of this node.'''
        raise NotImplementedError()

    @abstractmethod
    def _get_child(self, key):
        '''Get the child for an, or raise a KeyError.'''
        raise NotImplementedError()

    def get_child(self, key, default=Missing):
        try:
            return self._get_child(key)
        except KeyError:
            if default is Missing:
                raise
            return default


class GraphNode(Graphable):
    '''Base class for directed graph structures.

    A GraphNode is an object with a value and a set of named edges pointing to
    other nodes. The edge names are strings, and are unique. Thus, you can
    identify any path in a graph by a starting node and a list of strings.

    Each GraphNode subclass must satisfy these properties:

    1) It defines a key_iter() method that returns a iterable over strings.

    2) It defines a _get_child(key) method that takes a string and returns a
    value or raises a KeyError.

    3) For each key in key_iter(), _get_child(key) should return a value instead
    of raising a KeyError.


    It *may* also implement _clone_with(self, edges), which should create a new
    GraphNode copying any data particular to this node but with a new set of
    edges. This is not required (it is nonsensical for some node types), and
    will raise a NotImplementedError if it is called when not provided.


    Note that it is NOT required that all values to _get_child that will produce
    values be in key_iter() - GraphNodes are allowed to produce values for keys
    even if they don't list them in key_iter. This is useful for e.g. virtual
    nodes with infinitely many acceptable keys.
    '''
    __slots__ = ()

    # This is deliberately not abstract - you can create GraphNode subclasses
    # that don't support cloning
    def _clone_with(self, edges):
        '''Create a copy of self with a different set of edges.'''
        raise NotImplementedError()

    def edge_iter(self):
        '''Iterate over the (key, child) edges of this node.'''
        for key in self.key_iter():
            yield key, self.get_child(key)

    def child_iter(self):
        '''Iterate over the child nodes of this node.'''
        for _, child in self.edge_iter():
            yield child

    def __getitem__(self, key):
        return self.get_path(key)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get_path(self, path, default=Missing):
        if isinstance(path, (list, tuple)):
            path = tuple(path)
        else:
            path = (path,)
        if not path:
            return self
        try:
            sub = self.get_child(path[0])
        except KeyError:
            if default is Missing:
                raise
            return default
        if len(path) == 1:
            return sub
        return sub.get_path(path[1:], default)

    def _subgraph_helper(self, selector, deep, memo=None):
        if memo is not None and id(self) in memo:
            return memo[id(self)]
        if selector is True:
            if not deep:
                return self
            selector = [(k,True) for k in self.key_iter()]
        elif isinstance(selector, dict):
            selector = selector.items()
        else:
            selector = [(k,True) for k in selector]
        edges = [(key, self.get_child(key)._subgraph_helper(subsel, deep, memo))
            for (key, subsel) in selector]
        new_node = self._clone_with(edges)
        if memo is not None:
            memo[id(self)] = new_node
        return new_node

    def subgraph(self, selector=True):
        '''Select a subgraph of this graph.

        The selector should be one of:

        1. A dictionary whose keys are edge keys for this object; the returned graph
        will only include these edges. The values of the selector dictionary will be
        passed recursively to subgraph() on the children of this graph.

        2. An iterable of keys; this is a convenient shorthand for passing in
        {k:True for k in selector}

        3. True; the returned graph will be this graph.

        Note that wherever 2 or 3 is used, portions of the graph will be the same
        objects as in this graph; use copysubgraph() if you want a completely new
        graph.
        '''
        return self._subgraph_helper(selector, False)


    def copysubgraph(self, selector=True):
        '''Copy a subgraph of this graph.

        NOTE: this will raise a NotImplementedError for Graph subclasses that do
        not implement _clone_with.

        The argument is treated just like in select, but none of the nodes in
        the returned graph will actually be nodes from this graph - all will be
        copied.

        Note that this uses an internal memo dict, much like copy.deepcopy does, to
        ensure that nodes won't be copied twice. Thus, if this graph is not a tree,
        the returned graph will mimic the original structure where possible.

        '''
        return self._subgraph_helper(selector, True, dict())


    def all_equals(self, other):
        '''Test if this graph and all its children equal other.'''
        if self.value != other.value:
            return False
        kids = list(self.edge_iter())
        okids = list(other.edge_iter())
        if len(kids) != len(okids):
            return False
        return all(c1.all_equals(c2) for ((_,c1), (_,c2)) in zip(kids, okids))

    def unordered_equal(self, other):
        '''Like all_equals, but ignores ordering of children.'''
        if self.value != other.value:
            return False
        edges = set(self.key_iter())
        oedges = set(other.key_iter())
        if edges != oedges:
            return False
        for edge in edges:
            if not self[edge].unordered_equal(other[edge]):
                return False
        return True

class PlainGraphNode(GraphNode):
    '''Implementation of GraphNode using an OrderedDict.

    Nodes carry no information besides their edges.
    '''
    __slots__ = ['value', '_edges']
    def __init__(self, value=None, edges=(), **kwargs):
        '''Initialize the node.

        Arguments should match those of the dict constructor.

        All edge values should be GraphNodes, or CopyableGraphNodes if you plan
        to copy this graph, but this is not checked or enforced - functions like
        subgraph() will raise exceptions if this is untrue.
        '''
        self._edges = OrderedDict(edges, **kwargs)
        self.value = value

    def key_iter(self):
        return self._edges.keys()

    def _get_child(self, key):
        return self._edges[key]

    def _clone_with(self, edges):
        return type(self)(self.value, edges)

    @classmethod
    def build(cls, d):
        '''Construct a PlainGraphNode from a dictionary.

        The key '_self' in the dict will be the value of the new node; all other
        keys will be recursively added as children.

        For example:

        >>> v = PlainGraphNode.build({
        ...     '_self': 1,
        ...     'foo': {'_self':3},
        ...     'bar': {
        ...         'baz': {
        ...             '_self': "hello",
        ...         }
        ...     }
        ... })
        >>> v.value
        1
        >>> v['foo'].value
        3
        >>> v['bar'].value
        >>> v['bar','baz'].value
        'hello'
        '''
        if not isinstance(d, dict):
            return cls(d, [])
        edges = [(key, cls.build(value))
            for (key, value) in d.items() if key != '_self']
        return cls(d.get("_self"), edges)

    def add_edge(self, key, child):
        '''Add a new child, raising ValueError if this key is already used.'''
        if key in self:
            raise ValueError("Duplicate key: {0}".format(key))
        self.set_edge(key, child)

    def set_edge(self, key, child):
        '''Set the child for an edge.'''
        assert isinstance(child, GraphNode)
        self._edges[key] = child

    def set_path(self, path, value):
        if isinstance(path, basestring):
            path = path.split('.')
        if not path:
            raise ValueError("Cannot set value of empty path!")
        if len(path) == 1:
            return self.set_edge(path[0], value)
        return self.get_child(path[0]).set_path(path[1:], value)

    def pop_edge(self, key, default=Missing):
        '''Remove an edge, returning the child that was there.

        If the edge doesn't exist, returns default if provided, otherwise raises
        a KeyError.
        '''
        result = self._edges.pop(key, default)
        if result is Missing:
            raise KeyError(key)
        return result

    def __setitem__(self, key, child):
        self.set_edge(key, child)


def plain_copy(node):
    '''Convert any graph into a graph made of PlainGraphNodes.

    Converting a graph with loops will end poorly, by which I mean not at all.
    '''
    edges = [(key, plain_copy(child)) for (key, child) in node.edge_iter()]
    return PlainGraphNode(node.value, edges)


class GraphableGraphNode(GraphNode):
    '''Wrap any Graphable in a GraphNode.

    The values will be the Graphable and its children; the node structure will
    match that of the Graphable.
    '''
    def __init__(self, graphable):
        self.value = graphable

    def key_iter(self):
        return self.value.key_iter()

    def get_child(self, key, default=Missing):
        child = self.value.get_child(key, default)
        if isinstance(child, Graphable):
            return GraphableGraphNode(child)
        return PlainGraphNode(child)


class ObjectGraphNode(GraphNode):
    '''Wrap an arbitrary Python object in a GraphNode.

    get_child(key) functions like getattr, but wraps the returned attribute in
    an ObjectGraphNode.

    If the keygraph argument is specified, it should be a Graph whose key names
    are attribute names comprising this object's graph; in this case, key_iter
    will follow the keygraph's structure.

    If keygraph is not provided, then key_iter will return an empty iterator -
    you'll only be able to follow edges you know exist, not programatically
    discover them.
    '''
    def __init__(self, object, keygraph=None):
        self.value = object
        self.keygraph = keygraph

    def key_iter(self):
        if self.keygraph is None:
            return ()
        return self.keygraph.key_iter()

    def _get_child(self, key):
        child = getattr(self.value, key, Missing)
        if child is Missing:
            raise KeyError(key)
        if self.keygraph is not None:
            keygraph = self.keygraph.get_child(key, None)
        else:
            keygraph = None
        return ObjectGraphNode(child, keygraph)

def test_object_graph():
    class Bar(object):
        class foo(object):
            x = 12
            y = 17


    node = ObjectGraphNode(Bar, PlainGraphNode.build({'foo':{'x':None, 'y':None}}))
    assert set(node.key_iter()) == {'foo'}
    assert set(node['foo'].key_iter()) == {'x', 'y'}
    assert node['foo', 'x'].value == 12

    equiv = PlainGraphNode.build({
        '_self':Bar,
        'foo':{
            '_self': Bar.foo,
            'x': 12,
            'y': 17,
        },
    })
    assert equiv.unordered_equal(node)


if __name__ == '__main__':
    test_object_graph()