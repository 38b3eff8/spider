from celery import Celery


from ping import Pinger

BROKER_URL = 'redis://localhost:6379/1'
app = Celery('proxy', broker=BROKER_URL)


@app.task
def check_ip(ip):
    pinger = Pinger(target_host=ip)
    delay = pinger.ping()

    if delay is not None:
        pass
