from bs4 import BeautifulSoup
from sqlalchemy import func

from spider import Spider, response
import task

from model import Session, ProxyIP

spider = Spider('http://www.xicidaili.com/nt/1')
session = Session()

spider.update_config({
    "base": {
        "worker": 1
    },
    "log": {
        "level": "DEBUG"
    }
})


# @spider.proxy
# def get_proxy():
#     session = Session()

#     proxy_ip = session.query(ProxyIP).filter(
#         ProxyIP.delay <= 200).order_by(func.random()).first()

#     if proxy_ip:
#         return Proxy(proxy_ip.ip, proxy_ip.port, proxy_ip.proxy_type)
#     else:
#         return None


@spider.route('/nt/<int:id>')
def nt_page(id):
    print('id: {0}'.format(id))

    resp = response.response

    soup = BeautifulSoup(resp.text, 'lxml')
    ip_list = soup.select('#ip_list tr')
    for index in range(1, len(ip_list)):
        proxy_ip_dict = {}
        ip_row = ip_list[index]
        td_list = ip_row.select('td')

        proxy_ip_dict['ip'] = td_list[1].text
        proxy_ip_dict['port'] = td_list[2].text

        country_img = td_list[0].select('img')
        if country_img:
            country = country_img[0]['alt']
        else:
            country = ''
        proxy_ip_dict['country'] = country

        city_a = td_list[3].select('a')
        if city_a:
            city = td_list[3].select('a')[0].text
        else:
            city = ''
        proxy_ip_dict['city'] = city

        proxy_ip_dict['transparent'] = td_list[4].text

        schema = td_list[5].text
        if schema == 'socks4/5':
            return
        proxy_ip_dict['schema'] = schema.lower()

        task.check_ip.delay(proxy_ip_dict)
        # proxy_ip = session.query(ProxyIP).filter(
        #     ProxyIP.ip == proxy_ip_dict['ip']
        # ).first()

        # if not proxy_ip:
        #     proxy_ip = ProxyIP()
        #     proxy_ip.load_attr(proxy_ip_dict)
        #     session.add(proxy_ip)
        # session.commit()

if __name__ == '__main__':
    spider.run()
