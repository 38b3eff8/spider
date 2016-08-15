import telnetlib
from celery import Celery

from ping import Pinger
from model import Session, ProxyIP

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

    if delay is not None:
        try:
            tn = telnetlib.Telnet(
                proxy_ip_dict['ip'],
                proxy_ip_dict['port'],
                timeout=10
            )
        except Exception as e:
            return

        session = Session()
        proxy_ip = ProxyIP()
        proxy_ip.load_attr(proxy_ip_dict)
        proxy_ip.delay = delay * 1000
        session.add(proxy_ip)
        session.commit()
