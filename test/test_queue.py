from spider.queue import RedisQueue, Task


def test_redis_queue():
    q = RedisQueue()
    task = Task('http://www.zhihu.com')
    q.push_task(task)

    result = q.pop_task()
    assert result.url == task.url
