from spider.config import config


def test_get_config():
    assert config['base']['worker'] == 5
