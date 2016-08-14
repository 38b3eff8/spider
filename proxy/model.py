from secret import CONNECT_STRING

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(CONNECT_STRING)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class ProxyIP(Base):
    __tablename__ = 'proxy_ip'

    id = Column(Integer, primary_key=True)
    ip = Column(String)
    port = Column(Integer)
    country = Column(String)
    city = Column(String)
    proxy_type = Column(String)
    delay = Column(Float)

    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    def load_attr(self, proxy_ip_dict):
        if 'ip' in proxy_ip_dict:
            self.ip = proxy_ip_dict['ip']

        if 'port' in proxy_ip_dict:
            self.port = proxy_ip_dict['port']

        if 'country' in proxy_ip_dict:
            self.country = proxy_ip_dict['country']

        if 'city' in proxy_ip_dict:
            self.city = proxy_ip_dict['city']

        if 'proxy_type' in proxy_ip_dict:
            self.proxy_type = proxy_ip_dict['proxy_type']

    def __repr__(self):
        return "<ProxyIP(id={0} ip:port={1}:{2} country={3}) delay={4})>".format(self.id, self.ip, self.port, self.country, self.delay)


if __name__ == '__main__':
    Base.metadata.create_all(engine)
