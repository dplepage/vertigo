=========================================
 Vertigo: Some really simple graph tools
=========================================

Vertigo is a small collection of classes and functions for building and working
with graphs with labeled edges. This is useful because dictionaries are just
graphs with labeled edges, and objects in Python are just dictionaries, so
really this applies to pretty much all objects.

By convention, if you need to use many different features of vertigo and don't
want to import them all into your namespace, you should rename the module to
``vg``::

    >>> import vertigo as vg

Graphs
======

A vertigo ``GraphNode`` is, at its core, a combination of two things:

 * A *value*, which is any python object
 * A set of *edges*, which are unique string names pointing to other nodes

Many graphs you'll work with will be ``PlainGraphNode``s, which are the simplest
implementation of the above - each simply stores its value and has an internal
dictionary of its edges.

``PlainGraphNode``s can be constructed directly pretty easily::

    >>> g1 = vg.PlainGraphNode("This is a value", edges=dict(
    ...     e1=vg.PlainGraphNode("This is another value"),
    ...     e2=vg.PlainGraphNode("This node has more children", edges=dict(
    ...         sub_edge=vg.PlainGraphNode(400),
    ...     )),
    ... ))

In the above graph, g1 has the value "This is a value" and two children,
identified by the strings "e1" and "e2". The node along edge "e1" has the value
"This is another value", while the node along edge "e2" has the value "This node
has more chidlren", and itself has an edge labeled "sub_edge" going to a fourth
node whose value is the integer 400.

Often, though, you'll use *dynamic* graph nodes, which implement the same
``GraphNode`` interface but wrap some other object. Dynamic nodes don't store
their structure explicitly, but instead construct their edges and children on
the fly as they're requested. Conceptually, the relationship between plain
graphs and dynamic graphs is similar to the relationship between sequences and
iterators - one is a static structure, the other is generated as needed, and as
much as possible you should write your code so that it doesn't care about the
distinction.

You can define your own dynamic node types simply by inheriting from
``GraphNode``, making sure your subclass has a ``.value`` attribute (or
property), and defining the two functions ``._get_child(key)``, which should
either return the node along the edge named ``key`` or raise a ``KeyError``, and
``.key_iter()``, which should return an iterable of strings all of which will
work when passed into ``._get_child``.

See ``ObjectGraphNode`` and ``DictGraphNode`` in graph.py for examples of
dynamic graphs wrapping objects; the ``InfiniteGraphNode`` type also
demonstrates a dynamic graph that doesn't wrap an object.

In many cases you may have a dynamic graph but want to work with it as a static
graph. In this case you can invoke the ``plain_copy`` function, which takes a
graph and returns a new graph with identical structure and values to the input
graph, but made entirely out of ``PlainGraphNode``s. This is mainly useful when
the dynamic generation of your graph is slow and you expect to walk the graph
multiple times - converting to a plain graph essentially caches the dynamic
computation.

Don't use ``plain_copy`` on a graph with cycles or an ``InfiniteGraphNode``,
though, as it will run forever. You can use it on non-tree acyclic graphs, but
nodes that appear twice in the same tree will be duplicated. In the future
vertigo will support cycle- and duplicate-detection in a lot of these functions,
but it doesn't yet.


Ordering
--------

``PlainGraphNode`` uses a ``collections.OrderedDict`` for its edges, so it will
always preserve the order of edges. Bear in mind, though that if you create one
by passing in a normal ``dict`` of edges then the order will be chosen
arbitrarily (and nondeterministically in python 3.3 or later).

Usually you don't care, but when testing (doctesting in particular) it's often
convenient to fix the order of graph chidlren. You can do this by making sure to
use ``OrderedDict`` everywhere; there's also a ``GraphWrapper`` called
``SortedWrapper`` that behaves just like the wrapped graph but always returning
keys in sorted order. There's more discussion of ``GraphWrapper``s later in this
document.


ascii_tree
==========

Vertigo provides lots of helpful functions, but one of the most useful for
understanding (and debugging) graphs is ``ascii_tree``. It is based on the
``asciitree`` module (https://pypi.python.org/pypi/asciitree), and prints the
structure of graphs in a (fairly) human-readable way::

    >>> print(vg.ascii_tree(g1, sort=True))
    root: 'This is a value'
      +--e1: 'This is another value'
      +--e2: 'This node has more children'
         +--sub_edge: 400

The argument ``sort=True`` causes it to sort the edges before printing; in
general you won't need this, but it's very useful in doctests to ensure
consistent output. As mentioned under *Ordering* above, you can also do this
with a ``SortedWrapper``::

    >>> print(vg.ascii_tree(vg.SortedWrapper(g1), sort=False))
    root: 'This is a value'
      +--e1: 'This is another value'
      +--e2: 'This node has more children'
         +--sub_edge: 400



Building Graphs
===============

From nested dictionaries
------------------------

You can construct ``PlainGraphNode``s more succinctly using the helper fn
``from_dict``. This takes a nested dictionary and turns it into a graph. Every
dictionary key becomes an edge in the graph, except for the special key
``"_self"``, which indicates a node's value. If an edge points at another
dictionary, the graph will be constructed recursively; if it points to a non-
dictionary value ``v`` then it will be treated as ``{'_self':v}``. For example,
the above graph could also have been constructed via::

    >>> g2 = vg.from_dict(dict(
    ...     _self = "This is a value",
    ...     e1 =  "This is another value",
    ...     e2 = dict(
    ...          _self = "This node has more children",
    ...          sub_edge = 400,
    ...     ),
    ... ))
    >>> print(vg.ascii_tree(g2, sort=True))
    root: 'This is a value'
      +--e1: 'This is another value'
      +--e2: 'This node has more children'
         +--sub_edge: 400

The inverse of ``from_dict`` is named ``to_dict``. It has an optional argument
``minimize`` which, if true, uses as much shorthand as possible in the
generation::

    >>> vg.to_dict(g2, minimize=True) == dict(
    ...     _self = "This is a value",
    ...     e1 =  "This is another value",
    ...     e2 = dict(
    ...          _self = "This node has more children",
    ...          sub_edge = 400,
    ...     ),
    ... )
    True

Note that without ``minimize=True``, the ``e1`` and ``e2/sub_edge`` values would
have been dictionaries with the single key ``_self``; see the docs for
``to_dict`` for more details.

From flat dictionaries
----------------------

Another useful constructor is the ``from_flat``, which takes a flat dictionary
whose keys are paths. This is extremely useful for succinctly creating sparse
graphs::

    >>> g3 = vg.from_flat({
    ...     '': 'This is the root',
    ...     'foo': 'This is the value at "foo"',
    ...     'foo/bar/baz/qux/spam/fleem': 'Parents are created as needed.',
    ...     'x/a': 12,
    ...     'x/b': 14,
    ... })
    >>> print(vg.ascii_tree(g3, sort=True))
    root: 'This is the root'
      +--foo: 'This is the value at "foo"'
      |  +--bar: None
      |     +--baz: None
      |        +--qux: None
      |           +--spam: None
      |              +--fleem: 'Parents are created as needed.'
      +--x: None
         +--a: 12
         +--b: 14

The inverse of ``from_flat`` is unimaginatively named ``to_flat``, and, like ``to_dict``, has a ``minimize`` argument that produces the smallest dict that captures the structure::

    >>> vg.to_flat(g3, minimize=True) == {
    ...     '': 'This is the root',
    ...     'foo': 'This is the value at "foo"',
    ...     'foo/bar/baz/qux/spam/fleem': 'Parents are created as needed.',
    ...     'x/a': 12,
    ...     'x/b': 14,
    ... }
    True

Note that without ``minimize=True``, the dictionary would include keys for all
paths with ``None`` values as well, such as ``'foo/bar'`` and ``x``; see the
docs for ``to_flat`` for more details.


Traversing Graphs
=================

The ``GraphNode`` interface is reminiscent of a dict. You can get a specific
child via ``.get_child(key)`` or by using ``__getitem__``::

    >>> g1.value
    'This is a value'
    >>> g1.get_child('e1').value
    'This is another value'
    >>> g1['e1'] is g1.get_child('e1')
    True

``__getitem__`` also supports using key tuples for deeper lookup::

    >>> g1['e2', 'sub_edge'] is g1['e2']['sub_edge']
    True

You can iterate over the edge keys, the child nodes, or tuples of (key, child)
using the iterator functions ``.key_iter()``, ``.child_iter()``, and
``.edge_iter()``, respectively::

    >>> lsl = lambda iter: list(sorted(list(iter))) # for reliable doctests
    >>> lsl(g1.key_iter())
    ['e1', 'e2']
    >>> set(g1.child_iter()) == {g1['e1'], g1['e2']}
    True
    >>> edges = lsl(g1.edge_iter())
    >>> edges == [('e1', g1['e1']), ('e2', g1['e2'])]
    True

Thus, to recurse over an entire graph structure, you might do::

    >>> def print_graph(g, key='root', depth=0):
    ...     print('{}{}: {}'.format(' '*depth, key, g.value))
    ...     for key, child in lsl(g.edge_iter()):
    ...         print_graph(child, key, depth+1)
    >>> print_graph(g1)
    root: This is a value
     e1: This is another value
     e2: This node has more children
      sub_edge: 400



Graph Zipping
=============

One very powerful feature of vertigo is the ability to combine graphs with
similar structures. A common use case for this is labeling data - you have a
data structure that you wish to display somehow, and you want to label its
components, but you need different labels depending on the context. Then you
might build a graph out of your data and merge it with a graph of labels to get
labeled values that you could display.

You can zip two graphs together using the ``zip`` function, which takes two or
more graphs and produce a new graph where the value at each node is a tuple of
the corresponding values from the input graphs.

Zipping graphs requires you to provide a key merging function that determines
the structure of the new graph. This function must take a list of graphs and
return a list of keys that should be present in the new graph.

You can pass a function as the ``merge_fn`` argument of ``zip``, or you can pass
a string identifying one of the pre-made common functions. For example, the
string ``'first'`` identifies a merge function that simply returns the keys of
the first graph in the list, resulting in a zipped graph that has the same
structure as the first input graph.

See ``zip_fns.py`` for more information about the provided merging functions.

In addition to ``zip``, there is also an ``izip`` function. ``izip`` returns a
dynamic graph, generating zipped graph nodes as you request them; ``zip`` is
simply ``plain_copy`` composed with ``izip``.

The naming is meant to mimic python's ``zip`` vs ``izip``, where ``izip``
returns an iterator while ``zip`` returns a list. Much like with those,
``vg.zip`` returns a concrete graph, but will fail if the graph it's operating
on is infinite, while ``vg.izip`` may be doing more work as you traverse it but
won't create nodes until you need them, allowing it to work on infinite
structures.

More documentation
==================

More docs coming soon. Here are some quick helpful notes:

A ``GraphWrapper`` is a dynamic graph that wraps another graph to change its
behavior. For example, the ``MapWrapper`` has a function that it applies to all
values in the graph, much like the ``imap`` function in python. See
``wrappers.py`` for more info.

A ``Walker`` is a quick way of defining a function that walks a graph doing
processing. See ``walker.py`` for more info, but also know that a lot of the
time you don't actually need it - just write a function that walks the graph
directly, like the ``print_graph`` function defined earlier in this doc.

``merge_fns.py`` has some helpers for merging graphs, where a "merge" is really
just a zip followed by a map. It has some predefined mapping functions that are
specifically useful when merging. For example, to overlay one graph on another,
you zip them and then apply a map that replaces the tuple of values with the
first non-None value in the tuple.

``misc_fns.py`` defines some miscellaneous graph manipulators, like a function
that takes two graphs and returns the subgraph of one of them matching the
structure of the other. Look at the individual functions there to see what they
do.
