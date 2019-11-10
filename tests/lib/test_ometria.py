import logging
from lib import (ometria)
from importer import (main)


def test_write_results():
    status, count = ometria.write_results([], main.AUTH_BASIC_OMETRIA)
    assert status == 'OK'
    assert count == 0

    status, count = ometria.write_results([], '', logging=logging)
    assert status == 'ERROR'

    status, count = ometria.write_results([{'firstname': '',
                                            'lastname': '',
                                            'id': '00000000',
                                            'email': '',
                                            'status': ''}
                                           ], main.AUTH_BASIC_OMETRIA)

    assert status == 'OK'
    assert count == 1
