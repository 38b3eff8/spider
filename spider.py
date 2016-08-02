import threading
import requests
import re
import redis
import pickle
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup

int_number = re.compile('^[+,-]?\d+')
float_number = re.compile('^[+,-]?\d+.?\d+$')


class Route(object):
    def __init__(self):
        self.root = Node('/')

    def add(self, url, func):
        node = self.root

        parse_result = urlparse(url)
        urls = [url for url in parse_result.path.split('/') if url]
        if len(urls) == 0:
            node.func = func
        else:
            self._add(node, urls, func)

    def _add(self, node, urls, func):
        key = urls[0]
        keys = node.sub_node.keys()
        if key not in keys:
            node.sub_node[key] = Node(key, None)

        if len(urls[1:]) > 0:
            sub_node = node.sub_node.get(key)
            self._add(sub_node, urls[1:], func)
        else:
            node.sub_node[key].func = func

    def get_func(self, url):
        node = self.root
        args = {}
        if not isinstance(url, str):
            return None, args
        urls = [url for url in urlparse(url).path.split('/') if url != '']

        i = 0
        while len(node.sub_node) > 0 and len(urls) > i:
            sub_url = urls[i]
            i += 1
            for item in node.sub_node.values():
                if item.param_type == 'base':
                    if item.name != sub_url:
                        continue
                else:
                    value = item.get_value(sub_url)
                    if value is None:
                        continue
                    args[item.param_name] = value
                node = item
                break
            else:
                node = None
                break

        if node is None or i < len(urls):
            return None, args
        else:
            return node.func, args

    def search(self, url):
        func, args = self.get_func(url)
        if func is None:
            return False
        else:
            return True

    def __str__(self):
        return str(self.root.sub_node)


param_re = re.compile('<(int|string|float):([a-zA-Z_]\w+)>')


class Node(object):
    def __init__(self, name, func=None):
        self.name = name
        self.sub_node = {}
        self.func = func

        result = param_re.match(name)
        if result:
            self.param_type = result.group(1)
            self.param_name = result.group(2)

            if self.param_type == 'int':
                self.pattern = re.sub('<int:\w+>', '([+,-]{0,1}\d+)', self.name)
            elif self.param_type == 'string':
                self.pattern = re.sub('<string:\w+>', '\w+', self.name)
            elif self.param_type == 'float':
                self.pattern = re.sub('<float:\w+>', '([+,-]{0,1}\d+.{0,1}\d+)', self.name)
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


class Response(object):
    def __init__(self):
        self.req = {}

    def get_response(self):
        return self.req[threading.current_thread().ident]

    def add_response(self, pid, req):
        self.req[pid] = req


response = Response()


class Worker(threading.Thread):
    def __init__(self, spider):
        super().__init__()
        self.spider = spider

    def run(self):
        while True:
            if self.spider is None:
                # todo 记得错误处理
                return

            task = self.spider.pop_task()
            if task is None:
                continue
            url = task.url

            # todo 标记该网页已经被爬过
            r = requests.get(url, headers=self.spider.config.get('headers'))
            if r.status_code != 200:
                pass

            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.select('a'):
                href = a.get('href')
                sub_url = self.convert(href, url)
                if not isinstance(sub_url, str) or not sub_url.startswith('http'):
                    continue

                sub_task = Task(sub_url)
                self.spider.push_task(sub_task)

            func, args = self.spider.r.get_func(url)
            if func is None:
                continue
            response.add_response(threading.get_ident(), r)
            func(**args)

    @staticmethod
    def convert(href, url):
        parse_result = urlparse(url)
        href_result = urlparse(href)

        # todo: 过滤站外链接

        if href_result.netloc == '':
            return parse_result.scheme + "://" + parse_result.netloc + href_result.geturl()
        else:
            if href_result.netloc == parse_result.netloc:
                if href_result.scheme != '':
                    return href
                else:
                    return parse_result.scheme + "://" + href
            else:
                return None


class Task(object):
    def __init__(self, url, type=None):
        self.type = type
        self.url = url


user_agents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36",
]


class Config(object):
    def __init__(self):
        self.config = {
            'worker': 5,
            'headers': {
                "user-agent": user_agents[0]
            }
        }

    def get(self, key):
        return self.config.get(key)


class RedisQueue(object):
    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(host, port, db)
        self._redis.flushall()
        self._queue_lock = threading.Lock()

    def push_task(self, task, direct='left'):

        with self._queue_lock:
            if not self._redis.get(task.url):
                print('{0}\t{1}\t{2}\t{3}'.format(direct, self._redis.get(task.url), 'Push__in', task.url))
                if direct == 'left':
                    self._redis.lpush('task_queue', pickle.dumps(task))
                else:
                    self._redis.rpush('task_queue', pickle.dumps(task))
                self._redis.set(task.url, 1)
            else:
                print('{0}\t{1}\t{2}\t{3}'.format(direct, self._redis.get(task.url), 'Not_push', task.url))

    def pop_task(self):
        task = self._redis.rpop('task_queue')
        if task is not None:
            task = pickle.loads(task)
        return task


class Spider(object):
    def __init__(self, start_url):
        self.config = Config()
        self.r = Route()
        self.task_queue = RedisQueue()

        task = Task(start_url)
        self.push_task(task)

    def set_config(self, config=None):
        if not config:
            return

    def route(self, url):
        def _deco(func):
            self.r.add(url, func)

        return _deco

    def run(self):
        for i in range(self.config.get('worker')):
            Worker(self).start()

    def push_task(self, task):
        direct = 'left'
        if self.r.search(task.url):
            direct = 'right'
        self.task_queue.push_task(task, direct)

    def pop_task(self):
        return self.task_queue.pop_task()


# spider = Spider('http://www.mahua.com/xiaohua/1628976.htm')
spider = Spider('https://www.zhihu.com')

'''
@spider.route('/xiaohua/<int:id>.htm')
def test(id):
    result = response.get_response()
    soup = BeautifulSoup(result.text, "lxml")
    now = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))
    # print(now, id, threading.current_thread().ident, soup.select('h1'))
    with open('log.txt', 'a') as f:
        f.write('{0} {1} {2} {3}\n'.format(now, id, threading.current_thread().ident, soup.select('h1')))
'''


@spider.route('/question/<int:id>')
def test(id):
    r = response.get_response()
    print(r.status_code, '\t', r.url)


# test main
if __name__ == '__main__':
    spider.run()
