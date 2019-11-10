import json
from urllib import (request, parse, error)
from . import ssl_context


def write_results(results, authorization, logging=None):
    rq = request.Request('http://ec2-34-242-147-110.eu-west-1.compute.amazonaws.com:8080/record',
                         method='POST',
                         headers={'Authorization': authorization,
                                  'Content-Type': 'application/json'},
                         data=json.dumps(results).encode())

    try:
        with request.urlopen(rq, context=ssl_context.relaxed_context) as rsp:
            if rsp.getcode() == 201:
                data = json.loads(rsp.read().decode())
                return data['status'], data['content']
            else:
                if logging:
                    logging.error('Ometria api-write: response code: %d' % (rsp.getcode(), ))
    except error.HTTPError as e:
        if logging:
            logging.error('Ometria api-write: %s' % (e, ))

    return 'ERROR', -1

