import json


class Config(object):
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Config, cls).__new__(cls)
            import os
            with open(os.path.split(os.path.realpath(__file__))[0] + '/default.config.json', 'r') as f:
                config = json.load(f)
                cls._instance._config = config

        return cls._instance

    def __getitem__(self, key):
        return self._config.get(key)


config = Config()
