from .graph import Missing, plain_copy, PlainGraphNode
from .zip_fns import izip
from .misc_fns import imap

class Omit(object):
    def __repr__(self): return "Omit"
Omit = Omit()

def first(l, default=None):
    for val in l:
        return val
    return default

def overlay_helper(vals):
    for val in vals:
        if val is Omit:
            return None
        elif val not in [None, Missing]:
            return val
    return None

def last(l, default=None):
    return first(reversed(list(l)), default)

def skip(l, *vals):
    return (v for v in l if v not in vals)

common_joins = dict(
    zip = lambda vals: tuple(v if v is not Missing else None for v in vals),
    first_defined = lambda vals: first(skip(vals, Missing)),
    last_defined = lambda vals: last(skip(vals, Missing)),
    first_not_none = lambda vals: first(skip(vals, Missing, None)),
    last_not_none = lambda vals: last(skip(vals, Missing, None)),
    overlay = overlay_helper,
    overlay_reverse = lambda vals: overlay_helper(reversed(vals))
)

def imerge(*graphs, **kwargs):
    join_fn = kwargs.pop('join_fn')
    if join_fn in common_joins:
        join_fn = common_joins[join_fn]
    return imap(izip(*graphs, default=Missing, **kwargs), join_fn)

def merge(*graphs, **kwargs):
    cls = kwargs.pop('cls', PlainGraphNode)
    return plain_copy(imerge(*graphs, **kwargs), cls=cls)

def overlay(*graphs, **kwargs):
    '''Overlay a stack of graphs on top of each other.

    Behavior is much like zipping, except that the value of each node will not
    be a tuple of all graphs' values, but instead will be the first non-None
    value from any graph.

    Thus, overlay(x, y) has x's values wherever they're not None, and y's values
    elsewhere.

    If the kwarg 'reversed' is True, then instead each value will be the *last*
    non-None value.

    If the non-None value is the special singleton Omit, then the value will be
    None even if a later value is not None.

    overlay accepts the merge_fn kwarg of zip, but defaults to 'first'.

    '''
    kwargs.setdefault('merge_fn', 'first')
    if kwargs.pop('reversed', False):
        kwargs['join_fn'] = 'overlay_reverse'
    else:
        kwargs['join_fn'] = 'overlay'
    return merge(*graphs, **kwargs)

def assert_equals(g1, g2):
    from .misc_fns import ascii_tree
    assert g1.all_equals(g2), ascii_tree(g1)+'\n'+ascii_tree(g2)

def test_merge():
    from .zip_fns import zip
    from collections import OrderedDict as d
    tree1 = PlainGraphNode.build(d([
        ('_self', 'R'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', 'D'),
    ]))
    tree2 = PlainGraphNode.build(d([
        ('_self', "R.2"),
        ('a', None),
        ('c', "C.2"),
        ('d', Omit),
    ]))

    for merge_fn in ['first', 'last', 'union', 'intersection']:
        a = merge(tree1, tree2, join_fn='zip', merge_fn=merge_fn)
        b = zip(tree1, tree2, merge_fn=merge_fn)
        assert_equals(a, b)
    def m(join_fn):
        return merge(tree1, tree2, merge_fn='union', join_fn=join_fn)

    assert_equals(m('last_defined'), PlainGraphNode.build(d([
        ('_self', 'R.2'),
        ('a', d([
            ('_self', None),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', Omit),
        ('c', 'C.2'),
    ])))
    assert_equals(m(common_joins['last_defined']), PlainGraphNode.build(d([
        ('_self', 'R.2'),
        ('a', d([
            ('_self', None),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', Omit),
        ('c', 'C.2'),
    ])))
    assert_equals(m('first_defined'), PlainGraphNode.build(d([
        ('_self', 'R'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', 'D'),
        ('c', 'C.2'),
    ])))
    assert_equals(m('first_not_none'), PlainGraphNode.build(d([
        ('_self', 'R'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', 'D'),
        ('c', 'C.2'),
    ])))
    assert_equals(m('last_not_none'), PlainGraphNode.build(d([
        ('_self', 'R.2'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', Omit),
        ('c', 'C.2'),
    ])))
    assert_equals(overlay(tree1, tree2), PlainGraphNode.build(d([
        ('_self', 'R'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', 'D'),
    ])))
    assert_equals(overlay(tree1, tree2, reversed=True), PlainGraphNode.build(d([
        ('_self', 'R.2'),
        ('a', d([
            ('_self', 'A'),
            ('a-1', 'A-1'),
        ])),
        ('b', 'B'),
        ('d', None),
    ])))
    assert_equals(overlay(tree2, tree1), PlainGraphNode.build(d([
        ('_self', 'R.2'),
        ('a', 'A'),
        ('c', 'C.2'),
        ('d', None),
    ])))
    assert_equals(overlay(tree2, tree1, reversed=True), PlainGraphNode.build(d([
        ('_self', 'R'),
        ('a', 'A'),
        ('c', 'C.2'),
        ('d', 'D'),
    ])))
    assert_equals(overlay(), PlainGraphNode())
    assert_equals(merge(join_fn='first_defined'), PlainGraphNode())