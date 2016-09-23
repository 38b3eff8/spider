from urllib.parse import urlparse, urljoin

import requests
from lxml import etree

from .config import config


def create_worker(spider, response):
    router = spider.route
    task_queue = spider.task_queue

    config_proxy = config['base']['proxy']
    max_try_times = config['base']['max_try_times']

    headers = config['headers']

    kwargs = {
        "headers": headers
    }

    def worker():
        while True:
            task = task_queue.pop_task()
            if task is None:
                # todo: wait
                continue

            node, args = router.get_node(task.url)

            # todo: filter

            if config_proxy:
                proxy = spider.get_proxy()
                kwargs['proxies'] = proxy.get_proxies()

            try:
                r = requests.get(task.url, **kwargs)
            except ConnectionError as e:
                task.try_times += 1
                if task.try_times == max_try_times:
                    continue

                spider.push_task(task)

            if r.status_code < 200 or r.status_code >= 400:
                continue

            tree = etree.HTML(r.text)
            result = tree.xpath('//a')

            for item in result:
                href = item.attrib.get('href')
                sub_url = convert(href, task.url)
                if sub_url:
                    task_queue.push_url(sub_url)

            # todo: add to response
            response.
            node.func(**args)

    return worker


def convert(href, url):
    href = urljoin(url, href)

    url_result = urlparse(url)
    href_result = urlparse(href)

    if href_result.netloc == url_result.netloc and href_result.scheme == url_result.scheme:
        return href
    else:
        return None
