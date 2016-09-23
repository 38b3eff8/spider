from spider.router import Router, Node


def test_add_route():
    r = Router()
    r.add('/test', lambda: 'test')
    r.add('/test2/<int:id>', lambda id: id)
    r.add('/test/<int:id>', lambda: "test")


def test_get_node():
    r = Router()
    r.add('/test', lambda: 'test')
    r.add('/test2/<int:id>', lambda id: id)
    r.add('/test/<int:id>', lambda: "test")
    node, args = r.get_node('/test')

    assert isinstance(node, Node)
    assert node.name == 'test'

    node, args = r.get_node('/test2/1')
    assert isinstance(node, Node)
    assert node.func(**args) == args['id']


def test_search():
    r = Router()
    r.add('/test', lambda: 'test')
    r.add('/test2/<int:id>', lambda id: id)
    r.add('/test/<int:id>', lambda: "test")

    assert r.search('/test') is True
    assert r.search('/test3') is False
