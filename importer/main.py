import asyncio
import logging
import base64
import time
import datetime
import concurrent.futures
import os
import json
import signal
import sys
import math
from lib import (mailchimp, ometria)


logging.basicConfig(format='%(asctime)s %(levelname)s |%(module)s|%(funcName)s|%(lineno)d| %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

AUTH_BASIC_MAILCHIMP = 'Basic ' + base64.b64encode((':' + os.getenv('MAILCHIMP_APIKEY', '')).encode()).decode()
AUTH_BASIC_OMETRIA = os.getenv('OMETRIA_APIKEY', '')


async def reader_worker(worker_id, lid, items_per_request, rq_queue, w_queue, rst_queue, latest_timestamp,
                        leader=False,
                        only_one_loop=False):
    loop = asyncio.get_running_loop()
    while True:
        offset = await rq_queue.get()
        logging.debug(f'reader{worker_id}: reading {items_per_request} items from offset {offset+1}...')

        with concurrent.futures.ThreadPoolExecutor() as pool:
            params = (lid, offset, items_per_request, AUTH_BASIC_MAILCHIMP, latest_timestamp, logging)
            total, results = await loop.run_in_executor(pool, mailchimp.read_items, *params)
            rst_queue.put_nowait(('READER', len(results) if total != -1 else -1))

            if total > 0:
                if total - 1 < offset:
                    logging.warning(f'reader{worker_id}: items [%d, %d] are outside range due to '
                                    f'offset {offset} larger than total items {total}, lowering '
                                    f'"start_offset" may help.' % (offset + 1, offset + items_per_request))
                else:
                    logging.info(f'reader{worker_id}: items [%d, %d] of {total} read.'
                                 % (offset+1, offset + len(results)))
                    w_queue.put_nowait(results)

                    if leader:
                        logging.info(f'reader{worker_id}: adding all remaining (#%d) offsets to request queue.'
                                     % (math.ceil((total - offset - 1)/items_per_request) if offset < total else 0),)
                        while offset + items_per_request < total:
                            offset += items_per_request
                            rq_queue.put_nowait(offset)

                        rq_queue.task_done()
                        # leader worker task is complete.
                        break
            elif total == 0:
                logging.info(f'reader{worker_id}: no changes read.')

            # non-leader workers signal their completion.
            rq_queue.task_done()

        # testing friendly
        if only_one_loop:
            break


async def writer_worker(worker_id, w_queue, rst_queue, only_one_loop=False):
    loop = asyncio.get_running_loop()
    while True:
        results = await w_queue.get()
        logging.debug(f'writer{worker_id}: writing {len(results)} results.')

        with concurrent.futures.ThreadPoolExecutor() as pool:
            successful, count = await loop.run_in_executor(pool,
                                                           ometria.write_results,
                                                           *(results, AUTH_BASIC_OMETRIA, logging))
            rst_queue.put_nowait(('WRITER', count))
            logging.info('writer%d: wrote %d results with status "%s".' % (worker_id, count, successful))
        w_queue.task_done()

        # testing friendly
        if only_one_loop:
            break


async def sync(worker_count, lid, items_per_request, start_offset=0, latest_timestamp=None):
    logging.info(f'sync: starting for list "{lid}" with {worker_count} read/write workers...')

    # request, write and result queues
    rq_queue, w_queue, rst_queue = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
    start_timestamp = datetime.datetime.now()

    tasks = []
    for i in range(worker_count):
        # reader0 is the leader that populates the request queue after its successful data read
        tasks.append(asyncio.create_task(reader_worker(i, lid, items_per_request, rq_queue, w_queue, rst_queue,
                                                       latest_timestamp=latest_timestamp,
                                                       leader=i == 0)))
        # all writer[0-] are equals
        tasks.append(asyncio.create_task(writer_worker(i, w_queue, rst_queue)))

    start_time = time.monotonic()
    rq_queue.put_nowait(start_offset)
    await rq_queue.join()
    await w_queue.join()
    elapsed_seconds = time.monotonic() - start_time

    logging.info('sync: completed in %.1f (s) for list "%s".' % (elapsed_seconds, lid))

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    with_errors, total_reads, total_writes = False, 0, 0
    while not rst_queue.empty():
        worker, count = rst_queue.get_nowait()
        rst_queue.task_done()
        if count == -1:
            with_errors = True
        else:
            if worker == 'READER':
                total_reads += count
            if worker == 'WRITER':
                total_writes += count

    return not with_errors and total_reads == total_writes, start_timestamp, round(elapsed_seconds, 1), total_writes


def get_list_state(state):
    def get_value(field, default_value):
        return state[field] if field in state else default_value

    lid = None
    try:
        lid = state['list_id']
    except KeyError:
        logging.warning('failed to load "list_id", entry is ignored: %s' % (state,))

    latest_timestamp = None
    if 'latest_timestamp' in state and state['latest_timestamp']:
        try:
            latest_timestamp = datetime.datetime.fromisoformat(state['latest_timestamp'])
        except ValueError:
            logging.warning(f'failed to load "latest_timestamp", setting to "None"'
                            f' forcing "RELOAD" instead of "SYNC" for list "{lid}".')

    # Mailchimp will block more than 8 concurrent access so worker_count should be at maximum 8
    return lid, latest_timestamp, \
        get_value('start_offset', 0), get_value('items_per_request', 100), get_value('worker_count', 8)


async def go(only_one_loop=False):
    logging.info('controller: starting...')

    fn = 'state/state.json'
    while True:
        try:
            with open(fn, 'r') as state_file:
                states = json.loads(state_file.read())
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            logging.error(f'controller: loading state file "{fn}" failed!')
            sys.exit(1)

        logging.info('controller: checking all lists.')
        for state in states:
            lid, latest_timestamp, start_offset, items_per_request, worker_count = get_list_state(state)
            if not lid:
                continue

            if latest_timestamp is None or \
                    latest_timestamp + datetime.timedelta(seconds=7200) < datetime.datetime.now():
                logging.info(f'controller: processing list "{lid}", last updated on "{latest_timestamp}".')
                logging.info(f'controller: list "{lid}" requires "%s", firing...' %
                             ('SYNC' if latest_timestamp else 'LOAD',))

                successful, timestamp, elapsed_seconds, total_updates = \
                    await sync(worker_count, lid, items_per_request, start_offset, latest_timestamp)
                if successful:
                    state['latest_timestamp'], state['elapsed_seconds'], state['total_updates'] = \
                        timestamp.strftime('%Y-%m-%dT%H:%M:%S'), elapsed_seconds, total_updates
                    with open(fn, 'w') as new_state_file:
                        new_state_file.write(json.dumps(states, indent=2))
            else:
                logging.info(f'controller: list "{lid}" up to date, last updated on "{latest_timestamp}".')

        logging.info('controller: sleeping for 60 seconds.')
        await asyncio.sleep(60)

        if should_quit():
            logging.warning('controller: done.')
            break

        # testing friendly
        if only_one_loop:
            break


def should_quit():
    fn = 'state/controller.quit'
    try:
        if open(fn, 'r'):
            os.unlink(fn)
        return True
    except FileNotFoundError:
        return False


if __name__ == '__main__':
    def ctrl_c(sig, frame):
        logging.warning(f'controller: exiting on signal "{sig}/{frame}"...')
        sys.exit(0)

    signal.signal(signal.SIGINT, ctrl_c)
    asyncio.run(go())
