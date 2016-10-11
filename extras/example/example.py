# from spider import Spider, response, Proxy
from spider import Spider, response

from bs4 import BeautifulSoup
import time
import threading

# from sqlalchemy import func
#
# from proxy.model import Session, ProxyIP

spider = Spider('http://www.duzhebao.com/a/jW14Qj.htm')
spider.update_config({
    "base": {
        "worker": 1
    },
    "log": {
        "level": "debug"
    }
})

# @spider.proxy
# def get_proxy():
#     session = Session()
#
#     proxy_ip = session.query(ProxyIP).filter(
#         ProxyIP.delay <= 200).order_by(func.random()).first()
#
#     if proxy_ip:
#         return Proxy(proxy_ip.ip, proxy_ip.port, proxy_ip.proxy_type)
#     else:
#         return None


@spider.route('/a/<string:id>.htm')
def test(id):
    r = response.response
    soup = BeautifulSoup(r.text, "lxml")
    now = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))
    title_tag = soup.title.string
    print(title_tag)
    with open('log.txt', 'a') as f:
        f.write('{0} {1} {2} {3}\t{4}\n'.format(
            now,
            id,
            threading.current_thread().ident,
            title_tag,
            r.url)
        )


if __name__ == '__main__':
    spider.run()
