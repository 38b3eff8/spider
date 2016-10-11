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

    def update_config(self, new_config):
        merge_dict(self._config, new_config)


def merge_dict(d1, d2):
    for key, value in d2.items():
        old_value = d1.get(key, None)
        if old_value is None:
            d1[key] = value
            continue

        if not isinstance(value, old_value.__class__):
            print('config type error')
            return

        if isinstance(old_value, dict):
            merge_dict(old_value, value)
        else:
            d1[key] = value


config = Config()
