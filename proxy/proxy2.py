from spider.spider import Spider, response, Proxy
import task

from sqlalchemy import func
from model import Session, ProxyIP

spider = Spider('http://www.kuaidaili.com/free/intr/1')

spider.load_config_dict({
    "proxy": {
        "proxy": True
    },
    "base": {
        "worker": 1
    },
    "log": {
        "level": "debug"
    }
})


@spider.proxy
def get_proxy():
    session = Session()

    proxy_ip = session.query(ProxyIP).filter(
        ProxyIP.delay <= 200).order_by(func.random()).first()

    if proxy_ip:
        return Proxy(proxy_ip.ip, proxy_ip.port, proxy_ip.proxy_type)
    else:
        return None


@spider.route('/free/intr/<int:page>')
def intr_page(page):
    pass

if __name__ == '__main__':
    spider.run()
