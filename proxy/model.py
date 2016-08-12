from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class ProxyIP(Base):
    __tablename__ = 'proxy_ip'

    id = Column(Integer, primary_key=True)
    ip = Column(String)
    port = Column(Integer)
