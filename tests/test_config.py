from spider.config import config


def test_get_config():
    assert config['base']['worker'] == 5


def test_get_config_not_set():
    assert config['base'].get('test', 0) == 0


def test_update_config():
    new_config = {
        "base": {
            "worker": 1
        }
    }

    config.update_config(new_config)
    assert config['base']['worker'] == 1
