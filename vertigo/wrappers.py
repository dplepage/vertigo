from .graph import GraphNode

class GraphWrapper(GraphNode):
    '''Virtual graph that wraps an existing graph.

    GraphWrapper(g) behaves just like g. This class is more useful for its
    subclasses, which can augment existing graphs.

    >>> from .graph import PlainGraphNode, plain_copy
    >>> g = PlainGraphNode.build(dict(
    ...     _self = 'foo',
    ...     child = dict(
    ...         _self = 'bar',
    ...         child = 'baz',
    ...     ),
    ... ))
    >>> g2 = GraphWrapper(g)
    >>> g.all_equals(g2)
    True
    >>> g2.value
    'foo'
    >>> list(g2.key_iter())
    ['child']
    >>> g2['child', 'child'].value
    'baz'

    Note that this is a virtual graph - the child nodes are created dynamically
    as they're requested. Use vertigo.plain_copy() to convert this to a plain
    graph.

    >>> g['child'] is g['child']
    True
    >>> g2['child'] is g2['child'] # Dynamically generated each time
    False
    >>> g3 = plain_copy(g2)
    >>> type(g3)
    <class 'vertigo.graph.PlainGraphNode'>
    >>> g3['child'] is g3['child']
    True

    The class does a bit of introspection to define a _get_child that will work
    for many subclasses. If your subclass defines __slots__ and takes no args to
    __init__ except the values for the slots as kwargs, then you won't need to
    define _get_child yourself (unless you want to change it, of course)
    '''
    __slots__ = ('graph', )
    def __init__(self, graph, **kwargs):
        self.graph = graph
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def value(self):
        return self.graph.value

    def _get_child(self, key):
        d = {slot:getattr(self, slot) for slot in self._all_slots()}
        d['graph'] = self.graph[key]
        return type(self)(**d)

    def key_iter(self):
        return self.graph.key_iter()

    @classmethod
    def _all_slots(cls):
        return set(sum((getattr(c, '__slots__', ()) for c in cls.__mro__), ()))

class MapWrapper(GraphWrapper):
    '''GraphWrapper that filters values through a function.

    MappedGraphNode(g, fn) has precisely the same structure as g, but if n is a
    node of g then the corresponding node n' in the MappedGraphNode has n'.value
    = fn(n.value).

    >>> from .graph import PlainGraphNode
    >>> g = PlainGraphNode.build(dict(
    ...     _self = 'foo',
    ...     child = dict(
    ...         _self = 'bar',
    ...         child = 'baz',
    ...     ),
    ... ))
    >>> g2 = MapWrapper(g, fn=lambda val: ''.join(reversed(val)))
    >>> g2.value
    'oof'
    >>> g2['child', 'child'].value
    'zab'
    '''
    __slots__ = ('fn',)

    @property
    def value(self):
        return self.fn(self.graph.value)

class DefaultWrapper(GraphWrapper):
    '''
    GraphWrapper that fills non-existant areas with default values.

    >>> from .graph import PlainGraphNode
    >>> g = PlainGraphNode.build(dict(
    ...     _self = 'foo',
    ...     child = dict(
    ...         _self = 'bar',
    ...         child = 'baz',
    ...     ),
    ... ))
    >>> g['no_such_child'].value
    Traceback (most recent call last):
        ...
    KeyError: 'no_such_child'
    >>> g2 = DefaultWrapper(g, default="No value here!")
    >>> g2.value
    'foo'
    >>> g2['child'].value
    'bar'
    >>> g2['no_such_child'].value
    'No value here!'
    >>> g2['child', 'not_a_child', 'no_more_children'].value
    'No value here!'
    '''
    __slots__ = ('default', )
    @property
    def value(self):
        if self.graph:
            return self.graph.value
        return self.default

    def _get_child(self, key):
        if self.graph and key in self.graph:
            return super(DefaultWrapper, self)._get_child(key)
        d = {slot:getattr(self, slot) for slot in self._all_slots()}
        d['graph'] = None
        return type(self)(**d)

class StarWrapper(GraphWrapper):
    '''
    GraphWrapper that treats edges labeled '*' as matching all nonpresent keys.

    StarWrapper(g) is just like g, except that if you follow an edge from g that
    doesn't exist, but g has an edge labeled '*', you'll get the child at g['*']
    instead.

    >>> from .graph import PlainGraphNode
    >>> g = PlainGraphNode.build({
    ...     '_self': 'foo',
    ...     '*': dict(
    ...         _self = 'bar',
    ...         child = 'baz',
    ...     ),
    ... })
    >>> g['foo'].value
    Traceback (most recent call last):
        ...
    KeyError: 'foo'
    >>> g2 = StarWrapper(g)
    >>> g2['foo'].value
    'bar'
    >>> g2['anything', 'child'].value
    'baz'

    '''
    def _get_child(self, key):
        if key in self.graph or '*' not in self.graph:
            return super(StarWrapper, self)._get_child(key)
        return super(StarWrapper, self)._get_child('*')

class SortedWrapper(GraphWrapper):
    '''Wrapper whose key_iter is always in sorted order.

    This is primarily used for testing:

    >>> from .graph import PlainGraphNode as G
    >>> g = G("Root", [("foo", G("fooval")), ("bar", G("barval"))])
    >>> print(list(SortedWrapper(g).key_iter()))
    ['bar', 'foo']
    '''
    def key_iter(self):
        return sorted(self.graph.key_iter())
