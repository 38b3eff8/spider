from sqlalchemy import func
from model import Session, ProxyIP
import requests

import time

session = Session()

ips = session.query(ProxyIP).all()

for item in ips:
    pattern = "{scheme}://{ip}:{port}"

    proxy_str = pattern.format(**{
        "scheme": item.schema,
        "ip": item.ip,
        "port": item.port
    })

    proxies = {
        "https": proxy_str
    }
    try:
        start = time.time()
        r = requests.get('https://www.baidu.com', proxies=proxies, timeout=5)
        delay = time.time() - start
        if r.status_code == 200:
            print(proxies)
            item.delay = delay
            item.updated_at = func.now()
            session.commit()
    except Exception as e:
        print("fail")
