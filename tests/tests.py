from contextlib import contextmanager
from collections import OrderedDict as d
import textwrap

from vertigo.graph import PlainGraphNode, plain_copy, ObjectGraphNode
from vertigo.graph import Graphable, GraphableGraphNode
from vertigo.misc_fns import subgraph, ascii_tree, map
import vertigo.zip_fns as vgz

@contextmanager
def expecting(error_type):
    ename = error_type.__name__
    try:
        yield
    except error_type:
        return
    except Exception as e:
        ename2 = type(e).__name__
        msg = "Expected {}, got {}:'{}' instead".format(ename, ename2, e)
        raise Exception(msg)
    else:
        raise Exception("Expected {}".format(ename))

def test_graphable():
    try:
        Graphable()
    except TypeError:
        pass
    else:
        raise Exception("That should have failed.")

def test_basic():
    foonode = PlainGraphNode.build({
        '_self': 2,
        'bar': 3,
        'baz': 4,
    })
    g = PlainGraphNode.build({
        '_self': 1,
        'foo': foonode,
    })
    # value
    assert g.value == 1
    # iterators
    assert list(g.key_iter()) == ['foo']
    assert list(g.child_iter()) == [foonode]
    assert list(g.edge_iter()) == [('foo', foonode)]
    # get_child
    assert g.get_child('foo', None) is foonode
    assert g.get_child('fake', None) is None
    with expecting(KeyError):
        g.get_child('fake')
    # get_path
    assert g.get_path('foo') is foonode
    assert g.get_path(('foo',)) is foonode
    assert g.get_path(('foo', 'bar')) is foonode.get_path('bar')
    assert foonode.get_path('bar').value == 3
    with expecting(KeyError):
        g.get_path(('not', 'a', 'path'))
    assert g.get_path(('not', 'a', 'path'), None) is None
    assert g.get_path(()) is g
    assert g['foo'] is foonode
    assert g['foo', 'bar'] is foonode['bar']
    assert g[()] is g
    # __contains__
    assert 'foo' in g
    assert ('foo',) in g
    assert ('foo', 'bar') in g
    assert ('foo', 'quux') not in g
    assert () in g
    # equality
    assert g.all_equals(g)
    assert not g.all_equals(foonode)
    g2 = PlainGraphNode.build({
        '_self': 1,
        'foo': foonode,
        'extra': 'an extra node',
    })
    assert not g.all_equals(g2)
    # unordered equality
    assert g.unordered_equals(g)
    assert not g.unordered_equals(foonode)
    assert not g.unordered_equals(g2)
    flip_foo = PlainGraphNode(2)
    for key, node in reversed(list(foonode.edge_iter())):
        flip_foo.add_edge(key, node)
    assert not flip_foo.all_equals(foonode)
    assert flip_foo.unordered_equals(foonode)
    g3 = PlainGraphNode.build({
        '_self': 1,
        'foo': g2,
    })
    assert not g.unordered_equals(g3)


def test_plain_graph_node():
    # Not much to test because we used PGN to test GraphNode already
    foonode = PlainGraphNode.build({
        '_self': 2,
        'bar': 3,
        'baz': 4,
    })
    g = PlainGraphNode(1, foo=foonode)
    with expecting(ValueError):
        g.add_edge('foo', PlainGraphNode(5))
    assert g['foo'] is foonode
    g.set_edge('foo', PlainGraphNode(5))
    assert g['foo'] is not foonode
    assert g['foo'].value == 5
    g.set_edge('foo', foonode)
    assert g['foo', 'bar'].value == 3
    g.set_path(('foo', 'bar'), PlainGraphNode(5))
    assert g['foo', 'bar'].value == 5
    g['foo'].set_path('bar', PlainGraphNode(3))
    assert g['foo', 'bar'].value == 3
    with expecting(ValueError):
        g.set_path((), PlainGraphNode(5))
    assert g.pop_edge('foo') is foonode
    assert 'foo' not in g
    with expecting(KeyError):
        g.pop_edge('foo')
    assert g.pop_edge('foo', None) is None
    g['foo'] = foonode
    assert g['foo'] == foonode

def test_copy():
    g = PlainGraphNode.build({
        '_self': 1,
        'foo': {
            '_self': 2,
            'bar': 3,
            'baz': 4,
        },
    })
    g2 = plain_copy(g)
    assert g2.all_equals(g)
    assert g2 is not g

def test_object_graph():
    class Bar(object):
        class foo(object):
            x = 12
            y = 17
        class not_on_graph(object):
            x = 23


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

    assert node['not_on_graph', 'x'].value == 23
    assert list(node['not_on_graph'].key_iter()) == []
    with expecting(KeyError):
        node['not_an_attribute']

def test_graphable_graph():
    g = PlainGraphNode.build({
        '_self': 1,
        'foo': {
            '_self': 2,
            'bar': 3,
            'baz': 4,
        },
    })
    g2 = GraphableGraphNode(g)
    g3 = map(g2, fn=lambda v:v.value)
    assert g3.all_equals(g)

def test_zip():
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

    intersection = subgraph(union, {'a':[]})
    first = subgraph(union, ['a', 'b'])
    last = subgraph(union, d([
        ('a', []),
        ('c', True),
    ]))

    assert vgz.izip(tree1, tree2, merge_fn='union').all_equals(union)
    assert vgz.izip(tree1, tree2, merge_fn='intersection').all_equals(intersection)
    assert vgz.izip(tree1, tree2, merge_fn='first').all_equals(first)
    assert vgz.izip(tree1, tree2, merge_fn='last').all_equals(last)
    assert vgz.zip(tree1, tree2).all_equals(vgz.izip(tree1, tree2))

    with expecting(vgz.StructureMismatch):
        vgz.zip(tree1, tree2, merge_fn='strict')

    vgz.zip(tree1, tree1, merge_fn='strict')

    t1, t2 = vgz.unzip(vgz.zip(tree1, tree2, merge_fn='union'))
    assert ascii_tree(t1).strip() == textwrap.dedent('''
    root: 'Root'
      +--a: 'Value A'
      |  +--a-1: 'Value A-1'
      +--b: 'Value B'
      +--c: None
    ''').strip()
    assert ascii_tree(t2).strip() == textwrap.dedent('''
    root: "Root'"
      +--a: "Value A'"
      |  +--a-1: None
      +--b: None
      +--c: "Value C'"
    ''').strip()

def test_empty_zip():
    '''Sanity check for graphless/empty graph zips'''
    assert vgz.izip(merge_fn='union').all_equals(PlainGraphNode(()))
    assert vgz.izip(merge_fn='intersection').all_equals(PlainGraphNode(()))
    assert vgz.izip(merge_fn='first').all_equals(PlainGraphNode(()))
    assert vgz.izip(merge_fn='last').all_equals(PlainGraphNode(()))
    assert vgz.izip(PlainGraphNode(), merge_fn='union').all_equals(PlainGraphNode((None,)))
    assert vgz.izip(PlainGraphNode(), merge_fn='intersection').all_equals(PlainGraphNode((None,)))
    assert vgz.izip(PlainGraphNode(), merge_fn='first').all_equals(PlainGraphNode((None,)))
    assert vgz.izip(PlainGraphNode(), merge_fn='last').all_equals(PlainGraphNode((None,)))

