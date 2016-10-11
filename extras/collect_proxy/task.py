import telnetlib
from celery import Celery
from sqlalchemy import func

from ping import Pinger
from model import Session, ProxyIP

import requests

BROKER_URL = 'redis://localhost:6379/1'
app = Celery('proxy', broker=BROKER_URL)

app.conf.update(
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
)


@app.task
def check_ip(proxy_ip_dict):
    # todo: 这边接收的参数需要变成一个对象
    pinger = Pinger(target_host=proxy_ip_dict['ip'])
    delay = pinger.ping_once()

    if delay is None:
        print('ping {ip} timeout'.format(ip=proxy_ip_dict['ip']))
        return

    if delay is not None:
        proxies = {
            "http": '{type}://{ip}:{port}'.format(
                type=proxy_ip_dict['schema'],
                ip=proxy_ip_dict['ip'],
                port=proxy_ip_dict['port']
            )
        }

        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
        }

        try:
            r = requests.get('http://www.xicidaili.com/nt/1',
                             headers=headers, proxies=proxies, timeout=5)
        except Exception as e:
            print('{ip} request timeout'.format(ip=proxy_ip_dict['ip']))
            return

        if r.status_code != 200:
            print('{ip} request error'.format(ip=proxy_ip_dict['ip']))
            return

        session = Session()

        proxy_ip = session.query(ProxyIP).filter(
            ProxyIP.ip == proxy_ip_dict['ip']
        ).first()

        if proxy_ip:
            proxy_ip.delay = delay * 1000
            proxy_ip.updated_at = func.now()
        else:
            proxy_ip = ProxyIP()
            proxy_ip.load_attr(proxy_ip_dict)
            proxy_ip.delay = delay * 1000
            session.add(proxy_ip)

        session.commit()
        print('{ip} save success'.format(ip=proxy_ip_dict['ip']))
