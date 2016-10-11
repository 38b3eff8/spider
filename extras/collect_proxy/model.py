from secret import CONNECT_STRING

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(CONNECT_STRING)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class ProxyIP(Base):
    __tablename__ = 'proxy_ip'

    id = Column(Integer, primary_key=True)

    schema = Column(String)
    ip = Column(String, unique=True)
    port = Column(Integer)

    anonymous = Column(String)

    country = Column(String)
    province = Column(String)
    city = Column(String)
    telecom = Column(String)

    delay = Column(Float)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now())

    def load_attr(self, proxy_ip_dict):
        if 'schema' in proxy_ip_dict:
            self.proxy_type = proxy_ip_dict['schema']

        if 'ip' in proxy_ip_dict:
            self.ip = proxy_ip_dict['ip']

        if 'port' in proxy_ip_dict:
            self.port = proxy_ip_dict['port']

        if 'country' in proxy_ip_dict:
            self.country = proxy_ip_dict['country']

        if 'province' in proxy_ip_dict:
            self.province = proxy_ip_dict['province']

        if 'city' in proxy_ip_dict:
            self.city = proxy_ip_dict['city']

        if 'telecom' in proxy_ip_dict:
            self.telecom = proxy_ip_dict['telecom']

        if 'anonymous' in proxy_ip_dict:
            self.anonymous = proxy_ip_dict['anonymous']

    def __repr__(self):
        return "<ProxyIP(id={0} {1}://ip:port={2}:{3} country={4}) delay={5})>".format(self.id, self.schema, self.ip, self.port, self.country, self.delay)


if __name__ == '__main__':
    Base.metadata.create_all(engine)
