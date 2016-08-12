from celery import Celery


from ping import Pinger

BROKER_URL = 'redis://localhost:6379/1'
app = Celery('proxy', broker=BROKER_URL)

app.conf.update(
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
)


@app.task
def check_ip(ip):
    # todo: 这边接收的参数需要变成一个对象
    pinger = Pinger(target_host=ip)
    delay = pinger.ping_once()

    if delay is not None:
        with open('log.txt', 'a') as f:
            f.write('{0}\t{1}\n'.format(ip, delay * 1000))
