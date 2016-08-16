import threading
import re
import redis
import pickle
import json
import logging
import configparser

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
        self._config = Config()

        headers = {}
        for key, value in self._config['headers'].items():
            headers[key] = value

        self.kwargs = {
            "headers": headers
        }

        if self._config.getboolean('proxy', 'proxy', fallback=False):
            proxy = self.spider.get_proxy()
            if proxy:
                self.kwargs['proxies'] = proxy.get_proxies()

        self.logger = Spider.get_logger(
            'worker_{id}'.format(id=threading.current_thread().ident)
        )

    def run(self):
        while True:
            if self.spider is None:
                # todo 记得错误处理
                return

            task = self.spider.pop_task()
            if task is None:
                continue
            url = task.url
            self.logger.info('start download page {url}'.format(url=url))
            r = requests.get(url, **self.kwargs)
            if r.status_code != 200:
                pass

            self.logger.info('download page success {url}'.format(url=url))

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

    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Config, cls).__new__(cls)
            config = configparser.ConfigParser()
            config.read('default.ini')
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
        self._update_log_basicConfig()

        self.r = Route()
        self.task_queue = RedisQueue()

        task = Task(start_url)
        self.push_task(task)

    def load_config_file(self, filenames):
        self._config.read_files(filenames)

        self._update_log_basicConfig()

    def load_config_dict(self, d):
        self._config.read_dict(d)

        self._update_log_basicConfig()

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
        direct = 'left'
        if self.r.search(task.url):
            direct = 'right'
        self.task_queue.push_task(task, direct)

    def pop_task(self):
        return self.task_queue.pop_task()

    def _update_log_basicConfig(self):
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
        # format = self._config.get('log', 'format')

        kwargs = {
            "level": level,
            "format": '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        }

        display = self._config.get('log', 'display', fallback='console')
        if display == 'file':
            filename = self._config.get('log', 'filename')
            kwargs['filename'] = filename

        print(kwargs)

        logging.basicConfig(**kwargs)

    @staticmethod
    def get_logger(name):
        logger = logging.getLogger(name)
        # config = Config()
        # display = config.get('log', 'display', fallback='console')
        #
        # logger.addHandler(ch)

        return logger
