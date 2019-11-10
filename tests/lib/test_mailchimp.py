import logging
from lib import (mailchimp)
from importer import (main)


def test_read_items():
    total, results = mailchimp.read_items('', 0, 1, main.AUTH_BASIC_MAILCHIMP, logging=logging)
    assert total == -1
    assert results == []

    total, results = mailchimp.read_items('1a2d7ebf82', 0, 10, main.AUTH_BASIC_MAILCHIMP, logging=logging)
    assert total >= 0
    assert len(results) == 10

    for result in results:
        assert result['id']
        assert result['email']
        assert result['status']
        assert 'firstname' in result
        assert 'lastname' in result
