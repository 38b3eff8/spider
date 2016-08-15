import threading
import re
import redis
import pickle
import json
import logging

from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
import requests

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


class Response(object):

    def __init__(self):
        self.req = {}

    def get_response(self):
        return self.req[threading.current_thread().ident]

    def add_response(self, pid, req):
        self.req[pid] = req


response = Response()


class Proxy(object):

    def __init__(self, ip, port, proxy_type, user=None, password=None):
        self.ip = ip
        self.port = port
        self.proxy_type = proxy_type

        self.user = user
        self.password = password

    def get_proxies(self):
        if self.user:
            pattern = "{scheme}://{user}:{password}@{ip}:{port}"
        else:
            pattern = "{scheme}://{ip}:{port}"

        proxy_str = pattern.format(**{
            "scheme": self.proxy_type,
            "ip": self.ip,
            "port": self.port,
            "user": self.user,
            "password": self.password
        })

        return {
            "http": proxy_str,
            "https": proxy_str
        }


class Worker(threading.Thread):

    def __init__(self, spider):
        super().__init__()
        self.spider = spider

        self.kwargs = {
            "headers": self.spider.get_config('headers')
        }

        if self.spider.get_config('proxy'):
            proxy = self.spider.get_proxy()
            if proxy:
                self.kwargs['proxies'] = proxy.get_proxies()

    def run(self):
        while True:
            if self.spider is None:
                # todo 记得错误处理
                return

            task = self.spider.pop_task()
            if task is None:
                continue
            url = task.url

            r = requests.get(url, **self.kwargs)
            if r.status_code != 200:
                pass

            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.select('a'):
                href = a.get('href')
                sub_url = self.convert(href, url)
                if not isinstance(sub_url, str):
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
        href = urljoin(url, href)

        url_result = urlparse(url)
        href_result = urlparse(href)

        if href_result.netloc == url_result.netloc and href_result.scheme == url_result.scheme:
            return href
        else:
            return None


class Task(object):

    def __init__(self, url, type=None):
        self.type = type
        self.url = url


class Config(object):

    def __init__(self):
        import os
        with open(os.path.split(os.path.realpath(__file__))[0] + "/default_config.json", 'r') as f:
            self.config = json.load(f)

    def get_config(self, key):
        return self.config.get(key)

    def set_config(self, config):
        if isinstance(config, dict):
            Config._add_config(self.config, config)

    @staticmethod
    def _add_config(default_config, config):
        for key, value in config.items():
            if isinstance(value, dict):
                Config._add_config(default_config[key], value)
            else:
                default_config[key] = value


class RedisQueue(object):
    _VIEW_URL = 'view_url'
    _TASK_QUEUE = 'task_queue'

    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(host, port, db)
        self._redis.flushall()
        self._queue_lock = threading.Lock()

    def push_task(self, task, direct='left'):

        with self._queue_lock:
            if not self._redis.sismember(RedisQueue._VIEW_URL, task.url):
                self._redis.sadd(RedisQueue._VIEW_URL, task.url)
                # print('{0}\t{1}\t{2}\t{3}'.format(
                #     direct, self._redis.get(task.url), 'Push__in', task.url)
                # )
                if direct == 'left':
                    self._redis.lpush(RedisQueue._TASK_QUEUE,
                                      pickle.dumps(task))
                else:
                    self._redis.rpush(RedisQueue._TASK_QUEUE,
                                      pickle.dumps(task))
            else:
                # print('{0}\t{1}\t{2}\t{3}'.format(
                #     direct, self._redis.get(task.url), 'Not_push', task.url)
                # )
                pass

    def pop_task(self):
        task = self._redis.rpop(RedisQueue._TASK_QUEUE)
        if task is not None:
            task = pickle.loads(task)
        return task

    def is_view_url(self, url):
        return self._redis.sismember(RedisQueue._VIEW_URL, url)


class Spider(object):

    def __init__(self, start_url):
        self._config = Config()
        self._set_log_config()

        self.r = Route()
        self.task_queue = RedisQueue()

        task = Task(start_url)
        self.push_task(task)

    def set_config(self, config):
        self._config.set_config(config)

        self._set_log_config()

    def get_config(self, key):
        return self._config.get_config(key)

    def show_config(self):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self._config.config)

    def route(self, url):
        def _wrapper(func):
            self.r.add(url, func)

        return _wrapper

    def proxy(self, func):
        self.get_proxy = func

        def _wrapper():
            return func()

        return _wrapper

    def run(self):
        for i in range(self.get_config('worker')):
            Worker(self).start()

    def push_task(self, task):
        direct = 'left'
        if self.r.search(task.url):
            direct = 'right'
        self.task_queue.push_task(task, direct)

    def pop_task(self):
        return self.task_queue.pop_task()

    def _set_log_config(self):
        log_config = self.get_config('log')
        filename = log_config.get('filename')

        level_dict = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        log_level = log_config.get('level').lower()
        log_format = log_config.get('format') | | '%(asctime)s %(message)s'
        logging.basicConfig(
            format=log_format,
            filename=filename,
            level=level_dict[log_level]
        )
