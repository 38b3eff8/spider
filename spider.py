import threading
import re
import redis
import pickle
import json
import logging
import configparser
import queue

from urllib.parse import urlparse, urljoin

from lxml import etree
import requests

int_number = re.compile('^[+,-]?\d+')
float_number = re.compile('^[+,-]?\d+.?\d+$')


class Route(object):

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
                return None

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


class Response(object):

    def __init__(self):
        self.req = {}

    def get_response(self):
        return self.req[threading.current_thread().ident]

    def _add_response(self, pid, req):
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

    def __repr__(self):
        return "<Proxy {proxy}>".format(proxy=self.get_proxies())


class Worker(threading.Thread):

    def __init__(self, spider):
        super().__init__()
        self.spider = spider
        self._config = Config()

        self._filter = self._config.getboolean('base', 'filter')
        self._proxy = self._config.getboolean('proxy', 'proxy', fallback=False)

        self._logger = Spider.get_logger(
            'worker_{id}'.format(id=threading.current_thread().ident)
        )

        headers = {}
        for key, value in self._config['headers'].items():
            headers[key] = value

        self.kwargs = {
            "headers": headers
        }

        self._logger.debug('request headers: {headers}'.format(
            headers=self.kwargs['headers']))

    def run(self):
        while True:
            if self.spider is None:
                return

            task = self.spider.pop_task()
            if task is None:
                continue
            url = task.url

            node, args = self.spider.r.get_node(url)

            if self._filter and (not node or node.filter_type == 'exclude'):
                continue

            if self._proxy:
                proxy = self.spider.get_proxy()
                if proxy:
                    self.kwargs['proxies'] = proxy.get_proxies()
                    self._logger.debug(
                        'request proxy: {proxy}'.format(proxy=proxy))

            print(self.kwargs)

            try:
                self._logger.info('start download page {url}'.format(url=url))
                r = requests.get(url, **self.kwargs)
            except Exception as e:
                task.try_times += 1
                if task.try_times == self._config.getint('base', 'max_try_times', fallback=5):
                    continue
                self.spider.push_task(task)
                self._logger.debug('retry task {url} {try_times}'.format(
                    url=url, try_times=task.try_times))

            if r.status_code != 200:
                self._logger.info('http status code error {code} {url}'.format(
                    url=url, code=r.status_code))
                continue
            self._logger.info('http status code success {code} {url}'.format(
                url=url, code=r.status_code))

            tree = etree.HTML(r.text)
            result = tree.xpath('//a')

            for item in result:
                href = item.attrib.get('href')
                sub_url = self.convert(href, url)
                if sub_url:
                    self.spider.push_task(Task(sub_url))

            response._add_response(threading.get_ident(), r)
            node.func(**args)

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

    def __init__(self, url, type=None, try_times=0):
        self.type = type
        self.url = url
        self.try_times = try_times


class Config(object):

    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Config, cls).__new__(cls)
            config = configparser.ConfigParser()

            import os
            config.read(
                os.path.split(os.path.realpath(__file__))[0] + '/default.ini'
            )
            cls._instance._config = config

        return cls._instance

    def __getitem__(self, key):
        if key in self._config:
            return self._config[key]
        else:
            return None

    def read_files(self, filenames):
        self._config.read(filenames)

    def read_dict(self, d):
        self._config.read_dict(d)

    def get(self, *args, **kwargs):
        return self._config.get(*args, **kwargs)

    def getint(self, *args, **kwargs):
        return self._config.getint(*args, **kwargs)

    def getboolean(self, *args, **kwargs):
        return self._config.getboolean(*args, **kwargs)


class BaseQueue(object):
    pass


class SimpleQueue(object):

    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.view_set = set()
        self._queue_lock = threading.Lock()

    def push_task(self, task, level=0):
        with self._queue_lock:
            self.view_set.add(task.url)
            self.queue.put((-level, task))

    def pop_task(self):
        self.queue.get()

    def is_view_url(self, url):
        return url in self.view_set


class RedisQueue(object):
    _VIEW_URL = 'view_url'
    _TASK_QUEUE = 'task_queue'

    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(host, port, db)
        self._redis.flushall()
        self._queue_lock = threading.Lock()

    def push_task(self, task, level=0):

        with self._queue_lock:
            if not self._redis.sismember(RedisQueue._VIEW_URL, task.url):
                self._redis.sadd(RedisQueue._VIEW_URL, task.url)
                if level == 0:
                    self._redis.lpush(
                        RedisQueue._TASK_QUEUE,
                        pickle.dumps(task)
                    )
                else:
                    self._redis.rpush(
                        RedisQueue._TASK_QUEUE,
                        pickle.dumps(task)
                    )

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
        self._update_log_basic_config()

        self.r = Route()

        queue_type = self._config.get('base', 'queue')
        if queue_type == 'simple':
            self.task_queue = SimpleQueue()
        elif queue_type == 'redis':
            self.task_queue = RedisQueue()

        self.push_task(Task(start_url))

    def load_config_file(self, filenames):
        self._config.read_files(filenames)

        self._update_log_basic_config()

    def load_config_dict(self, d):
        self._config.read_dict(d)

        self._update_log_basic_config()

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
        worker = self._config.getint('base', 'worker', fallback=5)
        for i in range(worker):
            Worker(self).start()

    def push_task(self, task):
        level = self.get_priority(url=task.url)
        self.task_queue.push_task(task, level)
        Spider.get_logger('task queue').debug(
            'push {url} to task queue'.format(url=task.url))

    def pop_task(self):
        task = self.task_queue.pop_task()
        if task:
            Spider.get_logger('task queue').debug(
                'pop {url} from task queue'.format(url=task.url))
        else:
            Spider.get_logger('task queue').debug('task queue no task')
        return task

    def _update_log_basic_config(self):
        level_dict = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        level = level_dict[
            self._config.get('log', 'level', fallback='info').lower()
        ]

        kwargs = {
            "level": level,
            "format": '[%(asctime)s - %(levelname)s - %(name)s] - %(message)s'
        }

        display = self._config.get('log', 'display', fallback='console')
        if display == 'file':
            filename = self._config.get('log', 'filename')
            kwargs['filename'] = filename

        logging.basicConfig(**kwargs)

    @staticmethod
    def get_logger(name):
        logger = logging.getLogger(name)
        return logger

    def filter(self, include=None, exclude=None):
        if include:
            for url in include:
                self.r.add(url, filter_type='include')

        if exclude:
            for url in exclude:
                self.r.add(url, filter_type='exclude')

    def priority(self):
        def _wrapper(func):
            self.get_proxy = func
        return _wrapper

    @staticmethod
    def get_priority(url=None):
        level = 0
        if self.r.search(url):
            return 100
