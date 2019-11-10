import asyncio
import datetime
import pytest
from unittest.mock import (Mock, call, mock_open, patch)
from importer import (main)


def async_to_sync(af):
    def fun(*args, **kwargs):
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(af(*args, **kwargs))
        loop.close()
        return result
    return fun


@async_to_sync
async def my_controller():
    mo = mock_open(read_data='[]')
    with patch('importer.main.open', mo):
        await main.go(only_one_loop=True)


@pytest.mark.skip
def test_controller():
    my_controller()


def test_should_quit():
    assert not main.should_quit()


def test_get_list_state():
    lid, timestamp, offset, items_per_request, workers = main.get_list_state({'latest_timestamp': '',
                                                                              'worker_count': 4})
    assert lid is None

    lid, timestamp, offset, items_per_request, workers = main.get_list_state({'list_id': 'lid'})
    assert lid == 'lid'
    assert timestamp is None
    assert items_per_request == 100
    assert offset == 0
    assert workers == 8

    lid, timestamp, offset, items_per_request, workers = \
        main.get_list_state({'list_id': 'LID', 'latest_timestamp': '2019-01-01T00:00:00'})
    assert timestamp == datetime.datetime.fromisoformat('2019-01-01T00:00:00')


@pytest.mark.asyncio
async def test_writer_worker():
    w_queue, rst_queue = asyncio.Queue(), asyncio.Queue()
    w_queue.put_nowait([])

    main.logging = Mock()
    await main.writer_worker(0, w_queue, rst_queue, True)

    main.logging.assert_has_calls([call.debug('writer0: writing 0 results.'),
                                   call.info('writer0: wrote 0 results with status "OK".')],
                                  any_order=True)


@pytest.mark.asyncio
async def test_reader_worker():
    rq_queue, w_queue, rst_queue = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
    rq_queue.put_nowait(0)

    main.logging = Mock()
    await main.reader_worker(0, '', 1, rq_queue, w_queue, rst_queue, None, leader=True, only_one_loop=True)

    main.logging.assert_has_calls([call.debug('reader0: reading 1 items from offset 1...'),
                                   call.error('Mailchimp api-read: HTTP Error 404: Not Found')],
                                  any_order=True)

    rq_queue.put_nowait(0)

    main.logging = Mock()
    await main.reader_worker(0, '1a2d7ebf82', 1, rq_queue, w_queue, rst_queue, None, leader=True, only_one_loop=True)

    main.logging.assert_has_calls([call.debug('reader0: reading 1 items from offset 1...')],
                                  any_order=True)

    assert w_queue.qsize() == 1
    assert rq_queue.qsize() > 0

    for s in main.logging.method_calls:
        if s.startswith('call.info(\'reader0: items [1, 1] of'):
            assert True
        elif s.startswith('call.info(\'reader0: adding all remaining'):
            assert True
        elif s == 'call.debug(\'reader0: reading 1 items from offset 1...\')':
            assert True
        else:
            assert False
