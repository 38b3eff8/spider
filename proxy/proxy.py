from spider import Spider, response

from bs4 import BeautifulSoup
import redis

spider = Spider('http://www.xicidaili.com/nt/1')


@spider.route('/nt/<int:id>')
def nt_page(id):
    print('id: {0}'.format(id))

    resp = response.get_response()
    soup = BeautifulSoup(resp.text)
    ip_list = soup.select('#ip_list tr')
    for index in range(1, len(ip_list)):
        ip_row = ip_list[index]

        td_list = ip_row.select('td')

        country_img = td_list[0].select('img')
        if country_img:
            counrty = country_img[0]['alt']
        else:
            country = ''
        ip = td_list[1].text
        port = td_list[2].text
        city_a = td_list[3].select('a')
        if city_a:
            city = td_list[3].select('a')[0].text
        else:
            city = ''
        proxy_type = td_list[4].text


if __name__ == '__main__':
    spider.run()
