from spider import Spider, response

from bs4 import BeautifulSoup

spider = Spider('http://www.xicidaili.com/nt/1')


@spider.route('/nt/<int:id>')
def nt_page(id):
    print('id: {0}'.format(id))

    resp = response.get_response()
    soup = BeautifulSoup(resp.text)
    ip_list = soup.select('#ip_list tr')
    for index in range(1, len(ip_list)):
        ip_row = ip_list[index]
        print(ip_row.select('.country'))
        print()

if __name__ == '__main__':
    spider.run()
