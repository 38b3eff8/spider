import threading
import queue
import redis
import pickle

from abc import abstractclassmethod


class Task(object):
    def __init__(self, url, type=None, try_times=0):
        self.type = type
        self.url = url
        self.try_times = try_times


class BaseQueue(object):
    @abstractclassmethod
    def push_task(self, task, level):
        pass

    def push_url(self, url, type=None, try_times=0, level=0):
        task = Task(url, type, try_times)
        self.push_task(task, level)


class SimpleQueue(BaseQueue):
    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.view_set = set()
        self._queue_lock = threading.Lock()

    def push_task(self, task, level=0):
        self.queue.put((-level, task))
        self.view_set.add(task.url)

    def pop_task(self):
        task = self.queue.get()
        return task[1]

    def is_view_url(self, url):
        return url in self.view_set


class RedisQueue(BaseQueue):
    _VIEW_URL = 'view_url'
    _TASK_QUEUE = 'task_queue'

    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(host, port, db)
        self._redis.flushall()
        self._queue_lock = threading.Lock()

    def push_task(self, task, level=0):

        with self._queue_lock:
            if self._redis.sismember(RedisQueue._VIEW_URL, task.url):
                return

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
