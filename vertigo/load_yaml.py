from collections import OrderedDict

import yaml
import yaml.constructor

from .merge_fns import Omit
from .graph import GraphNode, PlainGraphNode, plain_copy

class VertigoYAMLLoader(yaml.Loader):
    """
    A YAML loader that loads ordered dictionaries and !Omit as vertigo.Omit
    Partly based on http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
    """
    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_plain_graph)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_plain_graph)
        self.add_constructor(u'!Omit', lambda *args, **kwargs: Omit)

    def construct_plain_graph(self, node):
        graph = PlainGraphNode()
        yield graph
        mapping = self.construct_mapping(node)
        for key, value in mapping.items():
            if key == '_self':
                graph.value = value
            else:
                if isinstance(value, GraphNode):
                    graph.add_edge(key, value)
                else:
                    graph.add_edge(key, PlainGraphNode(value))

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else: # pragma: no cover
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc: # pragma: no cover
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

def load_graph(string_or_file, cls=PlainGraphNode):
    '''Load a yaml file as a Vertigo graph.

    >>> from .misc_fns import ascii_tree
    >>> from .graph import StarGraphNode
    >>> s = ("""
    ... foo:
    ...     _self: 1
    ...     bar: hello
    ... bar:
    ...     _self: 3
    ...     '*': 'hi'
    ...     other: !Omit
    ... """).strip()
    >>> g = load_graph(s)
    >>> print(ascii_tree(g).strip())
    root: None
      +--foo: 1
      |  +--bar: 'hello'
      +--bar: 3
         +--*: 'hi'
         +--other: Omit
    >>> g['bar', 'hi'].value
    Traceback (most recent call last):
        ...
    KeyError: ('bar', 'hi')
    >>> g = load_graph(s, cls=StarGraphNode)
    >>> g['bar', 'hi'].value
    'hi'

    '''
    graph = yaml.load(string_or_file, Loader=VertigoYAMLLoader)
    if cls is not PlainGraphNode:
        graph = plain_copy(graph, cls=cls)
    return graph
