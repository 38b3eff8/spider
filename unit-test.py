import unittest

import spider


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.r = spider.Route()
        self.r.add('/test', lambda: 'test')
        self.r.add('/test2/<int:id>', lambda id: id)

    def test_add_route(self):
        self.r.add('/test/<int:id>', lambda: "test")

    def test_get_node(self):
        node, args = self.r.get_node('/test')
        self.assertIsInstance(node, spider.Node)
        self.assertEqual(node.name, 'test')

    def test_get_fun(self):
        func, args = self.r.get_func('/test')
        self.assertEqual(func(), 'test')

    def test_get_fun_args(self):
        func, args = self.r.get_func('/test2/1')
        self.assertEqual(func(**args), args['id'])


if __name__ == "__main__":
    unittest.main()
