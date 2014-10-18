from abc import ABCMeta, abstractmethod
from collections import OrderedDict
import sys

if sys.version >= '3': # pragma: no cover
    basestring = unicode = str


class Missing(object):
    # singleton placeholder for missing values
    pass
Missing = Missing()

_GraphableBase = ABCMeta('_GraphableBase', (object, ), {})

class Graphable(_GraphableBase):
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
    __slots__ = ()

    @abstractmethod
    def key_iter(self):
        '''Iterate over the edge keys of this node.'''

    @abstractmethod
    def _get_child(self, key):
        '''Get the child for an, or raise a KeyError.'''

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


    Note that it is NOT required that all values to _get_child that will produce
    values be in key_iter() - GraphNodes are allowed to produce values for keys
    even if they don't list them in key_iter. This is useful for e.g. virtual
    nodes with infinitely many acceptable keys.
    '''
    __slots__ = ()

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
                raise KeyError(path[0])
            return default
        if len(path) == 1:
            return sub
        try:
            return sub.get_path(path[1:], default)
        except KeyError as e:
            # Raise error on path to this point, because an error on ('foo',
            # 'bar', 'baz') is more helpful than an error on 'baz'.
            raise KeyError(*(path[0],)+e.args)


    def all_equals(self, other):
        '''Test if this graph and all its children equal other.'''
        if self.value != other.value:
            return False
        kids = list(self.edge_iter())
        okids = list(other.edge_iter())
        if len(kids) != len(okids):
            return False
        return all(c1.all_equals(c2) for ((_,c1), (_,c2)) in zip(kids, okids))

    def unordered_equals(self, other):
        '''Like all_equals, but ignores ordering of children.'''
        if self.value != other.value:
            return False
        edges = set(self.key_iter())
        oedges = set(other.key_iter())
        if edges != oedges:
            return False
        for edge in edges:
            if not self[edge].unordered_equals(other[edge]):
                return False
        return True

class PlainGraphNode(GraphNode):
    '''Implementation of GraphNode using an OrderedDict.

    Nodes carry no information besides their value and edges.

    >>> from .misc_fns import ascii_tree
    >>> print(ascii_tree(PlainGraphNode(12, foo=PlainGraphNode(14))))
    root: 12
      +--foo: 14

    PlainGraphNode will complain if given a non-graph or an invalid edge name:

    >>> PlainGraphNode(12, foo=14)
    Traceback (most recent call last):
        ...
    ValueError: Graph child is not a GraphNode: 14

    >>> PlainGraphNode(12, edges={1:PlainGraphNode()})
    Traceback (most recent call last):
        ...
    ValueError: Graph key is not a string: 1

    '''
    __slots__ = ('value', '_edges')
    def __init__(self, value=None, edges=(), **kwargs):
        '''Initialize the node.

        Arguments should match those of the dict constructor.

        All edge values should be GraphNodes.
        '''
        self._edges = OrderedDict(edges, **kwargs)
        self.value = value
        self._check_sanity()

    def _check_sanity(self):
        for key, child in self.edge_iter():
            if not isinstance(key, basestring):
                raise ValueError("Graph key is not a string: {}".format(key))
            if not isinstance(child, GraphNode):
                raise ValueError("Graph child is not a GraphNode: {}".format(child))

    def key_iter(self):
        return self._edges.keys()

    def _get_child(self, key):
        return self._edges[key]

    @classmethod
    def build(cls, d):
        '''Construct a PlainGraphNode from a dictionary.

        The key '_self' in the dict will be the value of the new node; all other
        keys will be recursively added as children.

        If any path ends in a GraphNode, that node will simply be added. If a
        path ends in a value `v` other than a GraphNode or a dictionary, then
        it will be treated as {'_self':v}

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

        This is equivalent to the above, using the implicit _self:

        >>> v2 = PlainGraphNode.build({
        ...     '_self': 1,
        ...     'foo': 3,
        ...     'bar': {
        ...         'baz': "hello",
        ...     }
        ... })
        >>> v2.value
        1
        >>> v2['foo'].value
        3
        >>> v2['bar'].value
        >>> v2['bar','baz'].value
        'hello'

        Existing GraphNodes will be preserved:

        >>> v3 = PlainGraphNode.build(dict(
        ...     sub1 = v,
        ...     sub2 = v2,
        ...     sub3 = dict(
        ...         _self = 1,
        ...         foo = 2,
        ...     )
        ... ))
        >>> v3['sub1'] is v
        True
        >>> v3['sub2'] is v2
        True
        >>> v3['sub3', 'foo'].value == 2
        True
        '''
        if isinstance(d, GraphNode):
            return d
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
        if isinstance(path, (list, tuple)):
            path = tuple(path)
        else:
            path = (path,)
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
        self.set_path(key, child)


def plain_copy(node, cls=PlainGraphNode):
    '''Convert any graph into a graph made of PlainGraphNodes.

    Converting a graph with loops will end poorly, by which I mean not at all.

    You can specify an alternate class instead of PlainGraphNode; the alternate
    must have the same constructor as PlainGraphNode, namely cls(value, edges).
    '''
    edges = [(key, plain_copy(child, cls)) for (key, child) in node.edge_iter()]
    return cls(node.value, edges)

def smart_plain_copy(node, cls=PlainGraphNode):
    '''Like plain_copy, but recurring nodes in the source are preserved.

    In other words, if the same node appears multiple times in the same graph,
    plain_copy() will create a new node for each occurrence, while
    smart_plain_copy will create one node and use it in both places.

    In particular, this means that smart_plain_copy can copy graphs containing
    cycles (while plain_copy() will exceed the maximum recursion depth):

    >>> g = PlainGraphNode()
    >>> g.add_edge('me', g)
    >>> g['me', 'me', 'me', 'me'] is g
    True
    >>> g2 = smart_plain_copy(g)
    >>> g2['me'] is g2
    True
    '''
    return _smart_plain_copy(node, cls, {})

def _smart_plain_copy(node, cls, cache):
    if node not in cache:
        cache[node] = cls(node.value)
        for (key, child) in node.edge_iter():
            cache[node].add_edge(key, _smart_plain_copy(child, cls, cache))
    return cache[node]


class GraphableGraphNode(GraphNode):
    '''Wrap any Graphable in a GraphNode.

    The values will be the Graphable and its children; the node structure will
    match that of the Graphable.
    '''
    __slots__ = ('value', )
    def __init__(self, graphable):
        self.value = graphable

    def key_iter(self):
        return self.value.key_iter()

    def _get_child(self, key, default=Missing):
        child = self.value.get_child(key, default)
        return GraphableGraphNode(child)


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
    __slots__ = ('value', 'keygraph')
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


class DictGraphNode(GraphNode):
    '''Wrap a nested dictionary in a GraphNode.

    If dn is a DictGraphNode wrapping dictionary d, then dn.get_child(key) will
    return a DictGraphNode wrapping d[key] (or raise KeyError if key not in d).

    A DictGraphNode's value is just the object it's wrapping; if that object is
    not a dictionary, then the node will have no outgoing edges.

    >>> d = dict(
    ...     foo = dict(
    ...         bar = 12,
    ...     ),
    ...     spam = "This is the spam value",
    ... )
    >>> dn = DictGraphNode(d)
    >>> dn.value is d
    True
    >>> dn['foo'].value is d['foo']
    True
    >>> dn['foo', 'bar'].value == 12
    True
    >>> list(sorted(dn.key_iter()))
    ['foo', 'spam']
    >>> list(sorted(dn['spam'].key_iter()))
    []
    >>> dn['nope']
    Traceback (most recent call last):
        ...
    KeyError: 'nope'
    >>> dn['spam', 'nope']
    Traceback (most recent call last):
        ...
    KeyError: ('spam', 'nope')

    '''
    __slots__ = ('value',)
    def __init__(self, target):
        self.value = target

    def key_iter(self):
        if isinstance(self.value, dict):
            return self.value.keys()
        return []

    def _get_child(self, key):
        if not isinstance(self.value, dict):
            raise KeyError(key)
        return DictGraphNode(self.value[key])

class JsonGraphNode(GraphNode):
    '''Wrap a json structure in a GraphNode.

    This is just like DictGraphNode except that it descends into lists and
    tuples as well, using the keys '0', '1', '2', etc. for the children.

    >>> d = dict(
    ...      foo = [
    ...         dict(bar = 12,),
    ...         dict(bar = 14,),
    ...     ],
    ...     spam = [1, 2, 3],
    ... )
    >>> jn = JsonGraphNode(d)
    >>> jn.value is d
    True
    >>> jn['foo'].value is d['foo']
    True
    >>> jn['foo', '0', 'bar'].value == 12
    True
    >>> jn['foo', '1', 'bar'].value == 14
    True
    >>> list(jn['foo', '1', 'bar'].key_iter())
    []
    >>> list(sorted(jn.key_iter()))
    ['foo', 'spam']
    >>> list(sorted(jn['spam'].key_iter()))
    ['0', '1', '2']
    >>> jn['nope']
    Traceback (most recent call last):
        ...
    KeyError: 'nope'
    >>> jn['spam', 'nope']
    Traceback (most recent call last):
        ...
    KeyError: ('spam', 'nope')
    >>> jn['spam', '0', 'nope']
    Traceback (most recent call last):
        ...
    KeyError: ('spam', '0', 'nope')

    '''
    __slots__ = ('value',)
    def __init__(self, target):
        self.value = target

    def key_iter(self):
        if isinstance(self.value, dict):
            return self.value.keys()
        if isinstance(self.value, (list, tuple)):
            return (str(i) for i in range(len(self.value)))
        return []

    def _get_child(self, key):
        if isinstance(self.value, (list, tuple)):
            try:
                return JsonGraphNode(self.value[int(key)])
            except (ValueError, KeyError):
                raise KeyError(key)
        if not isinstance(self.value, dict):
            raise KeyError(key)
        return JsonGraphNode(self.value[key])

class InfiniteGraphNode(GraphNode):
    '''An infinite graph with all possible edges and the same value everywhere.

    key_iter always returns an empty list, but attempting to access any child
    will always return this node itself:

    >>> g = InfiniteGraphNode("some value")
    >>> g.value
    'some value'
    >>> g['foo'] is g
    True
    >>> g['foo'].value
    'some value'
    >>> g2 = g['this', 'is', 'a', 'long', 'path']
    >>> g2 is g
    True
    >>> list(g.key_iter())
    []
    '''
    __slots__ = ('value',)
    def __init__(self, value):
        self.value = value

    def key_iter(self):
        return []

    def _get_child(self, key):
        return self


class DefaultGraphNode(PlainGraphNode):
    '''The graph analog to a defaultdict.

    This extension to PlainGraphNode adds a 'default' parameter; if you follow
    an edge that doesn't exist, you'll get a (dynamically generated) new node
    with the default value.

    Iteration will only yield keys that exist, either because they've already
    been defined or because they were dynamically generated by referencing them.

    Like an InfiniteGraphNode, a DefaultGraphNode is a graph of infinite size,
    as any edge you try to follow will be created for you. Unlike
    InfiniteGraphNode, each node is actually a separate object, created
    dynamically. Thus you can set the value at a specific path without changing
    the value everywhere.

    This makes DefaultGraphNode uncomfortably mutable - the act of trying to
    retrieve an edge with key k will automatically *create* that edge if it does
    not already exist. In general, you'll be able to write cleaner code with
    other graph types. The primary use case for DefaultGraphNode is when you
    need to construct a normal graph but for technical reasons it must be done
    iteratively, adding one edge at a time instead of specifying all of them at
    once. In this case you can use a DefaultGraphNode, but it's a good idea to
    convert it to a PlainGraphNode via plain_copy() as soon as possible.

    >>> g = DefaultGraphNode("default_value")
    >>> g.value
    'default_value'
    >>> g['foo'].value
    'default_value'
    >>> g['foo'] is g['foo']
    True
    >>> g['bar', 'baz', 'qux'].value = "hello"
    >>> g['bar', 'baz', 'fleem'].value = "goodbye"
    >>> list(g.key_iter())
    ['foo', 'bar']
    >>> list(g['bar', 'baz'].key_iter())
    ['qux', 'fleem']
    >>> g['bar', 'baz'].value
    'default_value'
    >>> g['bar', 'baz', 'qux'].value
    'hello'

    '''
    __slots__ = ('default', )
    def __init__(self, value=None, edges=(), default=Missing, **kwargs):
        super(DefaultGraphNode, self).__init__(value, edges, **kwargs)
        if default is Missing:
            default = value
        self.default = default

    def _get_child(self, key):
        try:
            return super(DefaultGraphNode, self)._get_child(key)
        except KeyError:
            new_node = type(self)(self.default, (), self.default)
            self._edges[key] = new_node
            return new_node


class StarGraphNode(PlainGraphNode):
    '''A PlainGraphNode with a '*'-labeled default edge.

    If this node has an edge labeled '*', then attempting to follow any edge not
    present from the node will follow the '*' edge instead.

    Note that this is different from a DefaultGraphNode - DefaultGraphNode
    generates new nodes when nonexistent edges are accessed, while StarGraphNode
    returns the node along the '*' edge.

    >>> g = StarGraphNode.build({
    ...     'x': 'foo',
    ...     '*': dict(
    ...         _self = 'bar',
    ...         sub1 = 1,
    ...         sub2 = 2,
    ...     ),
    ... })
    >>> g['x'].value # defined edges work normally
    'foo'
    >>> g['y'].value # undefined edges follow the '*' edge instead
    'bar'
    >>> g['z'].value # all undefined edges behave the same way
    'bar'
    >>> g['y'] is g['z'] # Undefined edges all lead to the same child
    True
    >>> isinstance(g['whatever'], StarGraphNode)
    True
    >>> # Nodes without '*' edges behave just like PlainGraphNodes
    >>> g['whatever']['foo']
    Traceback (most recent call last):
        ...
    KeyError: 'foo'
    '''
    __slots__ = ()
    def _get_child(self, key):
        if key not in self._edges and '*' in self._edges:
            return self._edges['*']
        return super(StarGraphNode, self)._get_child(key)


class PathGraph(GraphNode):
    '''An infinite, virtual graph where each node is the path to that node.

    >>> p = PathGraph()
    >>> p.value
    ()
    >>> p['foo', 'bar', 'baz'].value
    ('foo', 'bar', 'baz')
    >>> list(p.key_iter())
    []
    '''
    __slots__ = ('value',)
    def __init__(self, path=()):
        self.value = path

    def key_iter(self):
        return ()

    def _get_child(self, key):
        return PathGraph(self.value+(key,))

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
    assert equiv.unordered_equals(node)
