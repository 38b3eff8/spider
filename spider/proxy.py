class Proxy(object):
    def __init__(self, ip, port, proxy_type, user=None, password=None):
        self.ip = ip
        self.port = port
        self.proxy_type = proxy_type

        self.user = user
        self.password = password

    def get_proxies(self):
        if self.user:
            pattern = "{scheme}://{user}:{password}@{ip}:{port}"
        else:
            pattern = "{scheme}://{ip}:{port}"

        proxy_str = pattern.format(**{
            "scheme": self.proxy_type,
            "ip": self.ip,
            "port": self.port,
            "user": self.user,
            "password": self.password
        })

        return {
            "http": proxy_str,
            "https": proxy_str
        }

    def __repr__(self):
        return "<Proxy {proxy}>".format(proxy=self.get_proxies())
