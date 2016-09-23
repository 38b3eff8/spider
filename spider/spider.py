import threading

from .router import Router
from .config import config
from .worker import create_worker

response = threading.local()


class Spider(object):
    def __init__(self, start_url):
        self.r = Router()

        queue_type = config['base']['queue']
        if queue_type == 'simple':
            from .queue import SimpleQueue
            self.task_queue = SimpleQueue()
        elif queue_type == 'redis':
            from .queue import RedisQueue
            self.task_queue = RedisQueue()

        self.task_queue.push_url(start_url)

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
        worker = config['base']['worker']
        for i in range(worker):
            t = threading.Thread(target=create_worker(i, self, response))
            t.start()

    def filter(self, include=None, exclude=None):
        if include:
            for url in include:
                self.r.add(url, filter_type='include')

        if exclude:
            for url in exclude:
                self.r.add(url, filter_type='exclude')
