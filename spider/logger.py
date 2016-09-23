import logging
from .config import config

level_dict = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}


class Logger(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Logger, cls).__new__(cls)
            level = level_dict[config['log']['level'].lower()]
            kwargs = {
                "level": level,
                "format": '[%(asctime)s - %(levelname)s - %(name)s] - %(message)s'
            }

            display = config['log']['display']
            if display == 'file':
                filename = config['log']['filename']
                kwargs['filename'] = filename

            logging.basicConfig(**kwargs)

        return cls._instance

    @staticmethod
    def get_logger(name):
        return logging.getLogger(name)


logger = Logger()
