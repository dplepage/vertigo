#  ===========================================
#  = A collection of helpful graph functions =
#  ===========================================
from __future__ import print_function
try: # pragma: no cover
    from cStringIO import StringIO
except ImportError: # pragma: no cover
    from io import StringIO
from collections import OrderedDict

from .graph import GraphNode, PlainGraphNode, plain_copy, Missing
from .walker import bottom_up
from .wrappers import MapWrapper

@bottom_up
def make_path_graph(_value, path, children, _pre, cls=PlainGraphNode):
    '''Return a graph with the same structure whose values are their paths.

    >>> t = from_dict(dict(
    ...     x = 'X value',
    ...     y = 'Y value',
    ...     z = dict(
    ...         _self = 'Z value',
    ...         foo = 'bar',
    ...         baz = 'qux')))
    >>> dbg_print(make_path_graph(t))
    root: ()
      +--x: ('x',)
      +--y: ('y',)
      +--z: ('z',)
         +--baz: ('z', 'baz')
         +--foo: ('z', 'foo')
    '''
    return cls(path, children)


def imap(graph, fn):
    '''Return a virtual graph that passes each of graph's values through fn.'''
    return MapWrapper(graph, fn=fn)


def map(graph, fn, cls=PlainGraphNode):
    '''Return a copy of graph with each value replaced by fn(value).

    This is just plain_copy composed with imap.
    '''
    return plain_copy(imap(graph, fn=fn), cls=cls)


@bottom_up
def replace(_value, path, children, _pre, source_graph, default_value=Missing,
    cls=PlainGraphNode):
    '''Replace each value in the graph with the corresponding value of src_graph

    Missing values will be set to default_value, if it is provided, and will
    generate a KeyError otherwise.

    This should produce the same result as zipping and unzipping, that is,

    replace(g1, g2) == unzip(zip(g1, g2, merge_fn='first', default=default_value))[1]

    In other words, replace(g1, g2) yields a graph with the structure of g1 and
    the values of g2:

    >>> class DepthGraph(GraphNode):
    ...     def __init__(self, depth=0):
    ...         self.value = depth
    ...     def _get_child(self, key):
    ...         return DepthGraph(depth=self.value+1)
    ...     def key_iter(self): return ()
    >>> g1 = PlainGraphNode("Root", OrderedDict([
    ...     ('child1', PlainGraphNode("Child1")),
    ...     ('child2', PlainGraphNode("Child2", OrderedDict([
    ...         ('sub1', PlainGraphNode("Sub1"))])))]))
    >>> g2 = DepthGraph()
    >>> dbg_print(g1)
    root: 'Root'
      +--child1: 'Child1'
      +--child2: 'Child2'
         +--sub1: 'Sub1'
    >>> dbg_print(replace(g1, g2))
    root: 0
      +--child1: 1
      +--child2: 1
         +--sub1: 2

    Missing values:

    >>> g2 = PlainGraphNode("New Root",
    ...     child1 = PlainGraphNode("New Child1")
    ... )
    >>> dbg_print(replace(g1, g2))
    Traceback (most recent call last):
        ...
    KeyError: 'child2'
    >>> dbg_print(replace(g1, g2, default_value="DEFAULT"))
    root: 'New Root'
      +--child1: 'New Child1'
      +--child2: 'DEFAULT'
         +--sub1: 'DEFAULT'
    '''
    try:
        value = source_graph[path].value
    except KeyError:
        if default_value is Missing:
            raise
        value = default_value
    return cls(value=value, edges=children)


def fill_nones(graph, value):
    '''Replace every None in the graph with value.

    >>> g = from_dict(dict(
    ...     _self = None,
    ...     foo = None,
    ...     bar = "bar value",
    ...     baz = dict(
    ...         _self = "baz",
    ...         x = None,
    ...     ),
    ... ))
    >>> dbg_print(g)
    root: None
      +--bar: 'bar value'
      +--baz: 'baz'
      |  +--x: None
      +--foo: None
    >>> dbg_print(fill_nones(g, "FOO"))
    root: 'FOO'
      +--bar: 'bar value'
      +--baz: 'baz'
      |  +--x: 'FOO'
      +--foo: 'FOO'
    '''
    return map(graph, lambda v:value if v is None else v)


def pick(g1, g2):
    '''Replace every non-None value in g1 with g2[value].

    >>> g1 = from_dict(dict(
    ...     _self = (),
    ...     a = ("bar", "baz"),
    ...     b = dict(
    ...         _self = (),
    ...         x = None,
    ...         y = ("foo"),
    ...     ),
    ... ))
    >>> g2 = from_dict(dict(
    ...     _self = "G2 Root",
    ...     foo = "G2 Root:Foo",
    ...     bar = dict(
    ...         _self = "G2 Root:Bar",
    ...         baz = "G2 Root:Bar:Baz",
    ...     ),
    ... ))
    >>> dbg_print(g1)
    root: ()
      +--a: ('bar', 'baz')
      +--b: ()
         +--x: None
         +--y: 'foo'
    >>> dbg_print(pick(g1, g2))
    root: 'G2 Root'
      +--a: 'G2 Root:Bar:Baz'
      +--b: 'G2 Root'
         +--x: None
         +--y: 'G2 Root:Foo'
    '''
    def resolve(path):
        return g2[path].value if path is not None else None
    return map(g1, resolve)


def _ascii_tree(tree, buf, prefix, path, parents, sort=False):
    # adapted from asciitree module, https://pypi.python.org/pypi/asciitree/0.2
    # Print prefix if any
    if prefix:
        buf.write(prefix[:-3])
        buf.write('  +--')
    label = path[-1]
    # Check for recursive graph
    if tree in parents:
        index = '/'.join(path[:parents.index(tree)+1])
        buf.write('{} - recursive copy of {}\n'.format(label, index))
        return
    # Write out label and value
    buf.write('{}: {!r}\n'.format(label, tree.value))
    # Write out label and value
    kids = list(tree.edge_iter())
    nkids = len(kids)
    if sort:
        kids = sorted(kids)
    # Push the parent stack
    parents.append(tree)
    # Recurse on children
    for index, (key, child) in enumerate(kids):
        if index+1 == nkids:
            sub_prefix = prefix + '   '
        else:
            sub_prefix = prefix + '  |'
        _ascii_tree(child, buf, sub_prefix, path+(key,), parents, sort)
    # Pop the parent stack
    parents.pop()

def ascii_tree(tree, root='root', sort=False):
    '''Render a tree as a string.

    Mainly useful for debugging; see the dbg_print helper for a wrapper that
    actually calls print().

    Consider this graph:

    >>> t = from_dict(OrderedDict([
    ...     ('z', 'Z value'),
    ...     ('y', 'Y value'),
    ...     ('x', OrderedDict([
    ...         ('_self', 'X value'),
    ...         ('foo', 'bar'),
    ...         ('baz', 'qux')]))]))

    By default, ascii_tree will preserve the order of the tree:

    >>> print(ascii_tree(t))
    root: None
      +--z: 'Z value'
      +--y: 'Y value'
      +--x: 'X value'
         +--foo: 'bar'
         +--baz: 'qux'

    Pass sort=True to sort keys alphabetically, which is useful e.g. in doctests
    when the source dictionary isn't ordered:

    >>> print(ascii_tree(t, sort=True))
    root: None
      +--x: 'X value'
      |  +--baz: 'qux'
      |  +--foo: 'bar'
      +--y: 'Y value'
      +--z: 'Z value'
    '''
    buf = StringIO()
    _ascii_tree(tree, buf, '', (root,), [], sort)
    return buf.getvalue().strip()

def dbg_print(tree, sort=True):
    '''Shortand for print(ascii_tree(tree, sort=True))
    '''
    print(ascii_tree(tree, sort=sort))

def test_ascii_tree():
    import textwrap
    def cmp(s1, s2):
        assert s1 == textwrap.dedent(s2).strip(), s1
    t = from_dict(OrderedDict([
        ('z', 'Z value'),
        ('y', 'Y value'),
        ('x', OrderedDict([
            ('_self', 'X value'),
            ('foo', 'bar'),
            ('baz', 'qux'),
        ])),
    ]))
    cmp(ascii_tree(t), '''
        root: None
          +--z: 'Z value'
          +--y: 'Y value'
          +--x: 'X value'
             +--foo: 'bar'
             +--baz: 'qux'
    ''')
    cmp(ascii_tree(t, sort=True), '''
        root: None
          +--x: 'X value'
          |  +--baz: 'qux'
          |  +--foo: 'bar'
          +--y: 'Y value'
          +--z: 'Z value'
    ''')
    t['x', 'baz', 'nest'] = t['x']
    cmp(ascii_tree(t, sort=True), '''
        root: None
          +--x: 'X value'
          |  +--baz: 'qux'
          |  |  +--nest - recursive copy of root/x
          |  +--foo: 'bar'
          +--y: 'Y value'
          +--z: 'Z value'
    ''')

def _subgraph_helper(graph, selector, memo, cls):
    if id(graph) in memo:
        return memo[id(graph)]
    if selector is True:
        selector = [(k,True) for k in graph.key_iter()]
    elif isinstance(selector, dict):
        selector = selector.items()
    else:
        selector = [(k,True) for k in selector]
    edges = [(key, _subgraph_helper(graph.get_child(key), subsel, memo, cls))
        for (key, subsel) in selector]
    new_node = cls(graph.value, edges)
    memo[id(graph)] = new_node
    return new_node

def subgraph(graph, selector=True, cls=PlainGraphNode):
    '''Select a subgraph of a graph.

    The selector should be one of:

    1. A dictionary whose keys are edge keys for this object; the returned graph
    will only include these edges. The values of the selector dictionary will be
    passed recursively to subgraph() on the children of this graph.

    2. An iterable of keys; this is a convenient shorthand for passing in
    {k:True for k in selector}

    3. True; the returned graph will be this graph.

    Note that this uses an internal memo dict, much like copy.deepcopy does, to
    ensure that nodes won't be copied twice. Thus, if this graph is not a tree,
    the returned graph will mimic the original structure where possible.
    '''
    return _subgraph_helper(graph, selector, dict(), cls)

def test_subgraph():
    from collections import OrderedDict
    znode = PlainGraphNode.build(OrderedDict([
        ('_self', 'Z value'),
        ('foo', 'bar'),
        ('baz', 'qux'),
    ]))
    g = PlainGraphNode.build(OrderedDict([
        ('x', 'X value'),
        ('y', 'Y value'),
        ('z1', znode),
        ('z2', znode),
    ]))
    g1 = subgraph(g, ['z1', 'x', 'z2'])
    assert g1['z1'] is g1['z2']
    assert g1['x'].value == 'X value'


# TODO cycle detection?
def from_dict(d, cls=PlainGraphNode):
    '''Construct a graph from a dictionary.

    This is intended to replace PlainGraphNode.build.

    The key '_self' in the dict will be the value of the new node; all other
    keys will be recursively added as children.

    If any path ends in a GraphNode, that node will simply be added. If a
    path ends in a value `v` other than a GraphNode or a dictionary, then
    it will be treated as {'_self':v}

    For example:

    >>> v = from_dict({
    ...     '_self': 1,
    ...     'foo': {'_self':3},
    ...     'bar': {
    ...         'baz': {
    ...             '_self': "hello",
    ...         }
    ...     }
    ... })
    >>> dbg_print(v)
    root: 1
      +--bar: None
      |  +--baz: 'hello'
      +--foo: 3


    This is equivalent to the above, using the implicit _self:

    >>> v2 = from_dict({
    ...     '_self': 1,
    ...     'foo': 3,
    ...     'bar': {
    ...         'baz': "hello",
    ...     }
    ... })
    >>> dbg_print(v2)
    root: 1
      +--bar: None
      |  +--baz: 'hello'
      +--foo: 3


    Existing GraphNodes will be preserved:

    >>> v3 = from_dict(dict(
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
    >>> dbg_print(v2)
    root: 1
      +--bar: None
      |  +--baz: 'hello'
      +--foo: 3
    '''
    if isinstance(d, GraphNode):
        return d
    if not isinstance(d, dict):
        return cls(d, [])
    edges = [(key, from_dict(value, cls))
        for (key, value) in d.items() if key != '_self']
    return cls(d.get("_self"), edges)

# TODO cycle detection? maybe re-implement as a Walker?
def to_dict(graph, minimize=False, sorted=True):
    '''The inverse of from_dict - convert a graph to a dictionary.

    The returned dictionary will have the key _self pointing to the graph's
    value, and for each edge (key, child) of the graph the dict will map key to
    to_dict(child).

    >>> v = from_dict({
    ...     '_self': 1,
    ...     'foo': 3,
    ...     'bar': {
    ...         'baz': "hello",
    ...     }
    ... })
    >>> to_dict(v) == dict(_self = 1,
    ...     foo = dict(_self=3),
    ...     bar = dict(_self=None,
    ...         baz = dict(_self='hello'),
    ...     ),
    ... )
    True

    If the 'minimize' argument is True, then '_self' is omitted when it's None
    and nodes without children will be mapped directly to their values:

    >>> to_dict(v, minimize=True) == dict(_self = 1,
    ...     foo = 3,
    ...     bar = dict(
    ...         baz = 'hello',
    ...     ),
    ... )
    True

    The only case where a childless node won't map directly to its value is when
    that value is a dict or GraphNode, as this would confuse from_dict:
    >>> v = from_dict({
    ...     'foo': {'_self':dict(x=1, y=2)},
    ... })
    >>> to_dict(v, minimize=True) == dict(
    ...     foo = {'_self':dict(x=1, y=2)},
    ... )
    True

    '''
    d = OrderedDict() if sorted else {}
    if graph.value is not None or not minimize:
        d['_self'] = graph.value
    for key, child in graph.edge_iter():
        d[key] = to_dict(child, minimize, sorted)
    if minimize and list(d.keys()) in [[], ['_self']]:
        x = d.get('_self')
        if not isinstance(x, (GraphNode, dict)):
            return x
    return d


def from_flat(d, cls=PlainGraphNode, sep='/'):
    '''Construct a graph from a flat dict.

    The keys should all be paths, or path strings separated by sep (default
    '/').

    If sep is None, then the keys must be actual paths (i.e. tuples of strings)

    The value for each key will be the value of the node at that path:

    >>> v = from_flat({
    ...     'foo/bar': "A bar value",
    ...     'foo/baz/qux': 12,
    ...     'spam':18,
    ... })
    >>> dbg_print(v)
    root: None
      +--foo: None
      |  +--bar: 'A bar value'
      |  +--baz: None
      |     +--qux: 12
      +--spam: 18

    Note that empty path segments are ignored.

    >>> v = from_flat({
    ...     '':"This is the root",
    ...     '/foo//bar//':"This is foo/bar",
    ... })
    >>> dbg_print(v)
    root: 'This is the root'
      +--foo: None
         +--bar: 'This is foo/bar'

    This does mean that you can have two keys that are actually the same path,
    for example '/foo/bar' and 'foo/bar/'. Don't do this - from_flat detects
    this and yells at you:

    >>> v = from_flat({
    ...     '/foo//bar//':"This is foo/bar",
    ...     '///foo/bar':"But so is this",
    ... })
    Traceback (most recent call last):
        ...
    ValueError: Duplicate path 'foo/bar'

    Path keys are used directly:
    >>> v = from_flat({
    ...     (): "Root value",
    ...     ('foo', 'bar', 'baz'): "Value at foo/bar/baz",
    ... })
    >>> dbg_print(v)
    root: 'Root value'
      +--foo: None
         +--bar: None
            +--baz: 'Value at foo/bar/baz'

    This provides you with another opportunity to screw up:
    >>> v = from_flat({
    ...     'foo/bar':"This is foo/bar",
    ...     ('foo', 'bar'):"But so is this",
    ... })
    Traceback (most recent call last):
        ...
    ValueError: Duplicate path 'foo/bar'
    '''
    root = cls()
    for key, val in d.items():
        if sep and not isinstance(key, (list, tuple)):
            path = [bit for bit in key.split(sep) if bit]
        else:
            path = key
        target = root
        for bit in path:
            if bit not in target:
                new_node = PlainGraphNode()
                target.add_edge(bit, new_node)
            target = target[bit]
        if target.value:
            raise ValueError("Duplicate path '{}'".format(sep.join(path)))
        target.value = val
    return root

def _tf_helper(graph, prefix, minimize, sep):
    d = {}
    for key, child in graph.edge_iter():
        if sep:
            sub_prefix = sep.join([prefix, key]) if prefix else key
        else:
            sub_prefix = prefix + (key,) if prefix else (key,)
        d.update(_tf_helper(child, sub_prefix, minimize, sep))
    if graph.value is not None or not minimize or not d:
        d[prefix] = graph.value
    return d

def to_flat(graph, minimize=False, sep='/'):
    '''The inverse of from_flat.

    >>> d = {
    ...     'foo/bar': "A bar value",
    ...     'foo/baz/qux': 12,
    ...     'spam':None,
    ... }
    >>> to_flat(from_flat(d)) == {
    ...     '': None,
    ...     'foo': None,
    ...     'foo/bar': "A bar value",
    ...     'foo/baz': None,
    ...     'foo/baz/qux': 12,
    ...     'spam': None,
    ... }
    True

    If minimize=True is specified, then any None values that can be omitted
    without changing the structure of the graph will be:

    >>> to_flat(from_flat(d), minimize=True) == {
    ...     'foo/bar': "A bar value",
    ...     'foo/baz/qux': 12,
    ...     'spam': None,
    ... }
    True

    In the above case, the root, "foo", and "foo/baz" are omitted because their
    values are None and their structure is implied by other, non-None keys.
    "spam" is kept because without it there would be no record of an edge
    labeled "spam".

    Like 'from_flat', you can override the separator:

    >>> to_flat(from_flat(d), minimize=True, sep=" :-: ") == {
    ...     'foo :-: bar': "A bar value",
    ...     'foo :-: baz :-: qux': 12,
    ...     'spam': None,
    ... }
    True

    If sep is None, then paths will be returned intead of path strings:

    >>> to_flat(from_flat(d), minimize=True, sep=None) == {
    ...     ('foo', 'bar'): "A bar value",
    ...     ('foo', 'baz', 'qux'): 12,
    ...     ('spam',): None,
    ... }
    True

    '''
    return _tf_helper(graph, '', minimize, sep)

class AppliedGraphNode(GraphNode):
    '''GraphNode that applies a function graph to another graph.

    See apply().
    '''
    __slots__ = ('source_graph', 'fn_graph')
    def __init__(self, source_graph, fn_graph):
        self.source_graph = source_graph
        self.fn_graph = fn_graph

    @property
    def value(self):
        if self.fn_graph.value is None:
            return self.source_graph.value
        return self.fn_graph.value(self.source_graph.value)

    def key_iter(self):
        return self.source_graph.key_iter()

    def _get_child(self, key):
        src_child = self.source_graph[key]
        fn_child = self.fn_graph.get_child(key, None)
        if fn_child is None:
            return src_child
        return AppliedGraphNode(src_child, fn_child)

def apply(source_graph, fn_graph):
    '''
    Apply a graph of functions to the values in a graph.

    This is similar to map(), but instead of applying the same function to every
    value it takes a graph of functions:

    >>> g = from_flat({
    ...     'x': 12,
    ...     'x/y': 14,
    ...     'a': 9,
    ...     'a/b/c/d': 12
    ... })
    >>> # Double /x, subtract two from /x/y/, set /a/b/ to 100
    >>> fn_g = from_flat({
    ...     'x': lambda x:x*2,
    ...     'x/y': lambda x:x-2,
    ...     'a/b': lambda v: 100,
    ... })
    >>> result = apply(g, fn_g)
    >>> dbg_print(result)
    root: None
      +--a: 9
      |  +--b: 100
      |     +--c: None
      |        +--d: 12
      +--x: 24
         +--y: 12

    Note that values without corresponding functions (like /a in the above) are
    unchanged. Moreover, when the function tree runs out, the resulting graph
    will actually *be* the source graph:

    >>> result['a'] is g['a']
    False
    >>> result['a', 'b', 'c'] is g['a', 'b', 'c']
    True

    '''
    return AppliedGraphNode(source_graph, fn_graph)