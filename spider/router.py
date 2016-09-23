import re
from urllib.parse import urlparse

int_number = re.compile('^[+,-]?\d+')
float_number = re.compile('^[+,-]?\d+.?\d+$')

param_re = re.compile('<(int|string|float):([a-zA-Z_]\w+)>')


class Node(object):
    def __init__(self, name, func=None, filter_type='include'):
        self.name = name
        self.sub_node = {}
        self.func = func
        self.filter_type = filter_type

        result = param_re.match(name)
        if result:
            self.param_type = result.group(1)
            self.param_name = result.group(2)

            if self.param_type == 'int':
                self.pattern = re.sub(
                    '<int:\w+>', '([+,-]{0,1}\d+)', self.name)
            elif self.param_type == 'string':
                self.pattern = re.sub('<string:\w+>', '\w+', self.name)
            elif self.param_type == 'float':
                self.pattern = re.sub(
                    '<float:\w+>', '([+,-]{0,1}\d+.{0,1}\d+)', self.name)
        else:
            self.param_type = 'base'

    def add(self, node):
        self.sub_node[node.name] = node

    def get_value(self, sub_url):
        result = re.match(self.pattern, sub_url)

        funcs = {
            'int': lambda param: int(param.group(1)),
            'string': lambda param: param.group(1),
            'float': lambda param: float(param.group(1))
        }

        if result is None:
            return None
        return funcs[self.param_type](result)

    def __str__(self):
        return '[' + self.name + ' ' + str(self.sub_node) + ']'


class Router(object):
    def __init__(self):
        self.root = Node('/')

    def add(self, url, func=None, filter_type='target'):
        node = self.root

        def _add(node, parts):
            key = parts[0]
            keys = node.sub_node.keys()
            if key not in keys:
                node.sub_node[key] = Node(key, None)

            if len(parts[1:]) > 0:
                sub_node = node.sub_node.get(key)
                _add(sub_node, parts[1:])
            else:
                node.sub_node[key].func = func
                node.filter_type = filter_type

        parse_result = urlparse(url)
        parts = [part for part in parse_result.path.split('/') if part]
        if len(parts) == 0:
            node.func = func
        else:
            _add(node, parts)

    def get_node(self, url):
        parts = [part for part in urlparse(url).path.split('/') if part != '']
        args = {}

        def _get_node(node, parts):
            if not parts:
                return node
            part = parts[0]

            for sub_node in node.sub_node.values():
                if sub_node.param_type == 'base':
                    if sub_node.name != part:
                        continue
                else:
                    value = sub_node.get_value(part)
                    if value is None:
                        continue
                    args[sub_node.param_name] = value

                if not len(sub_node.sub_node):
                    return sub_node
                else:
                    return _get_node(sub_node, parts[1:])
            else:
                return None

        return _get_node(self.root, parts), args

    def search(self, url):
        node, args = self.get_node(url)
        if node is None:
            return False
        else:
            return True

    def __str__(self):
        return str(self.root.sub_node)
