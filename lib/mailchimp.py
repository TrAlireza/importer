import json
from urllib import (request, parse)
from . import ssl_context


def read_items(lid, offset, count, authorization, latest_timestamp=None, logging=None):
    fields = ['id', 'email_address', 'unique_email_id', 'status', 'merge_fields']
    query_string = {'fields': ','.join(['members.' + f for f in fields] + ['total_items']),
                    'count': count,
                    'offset': offset}
    if latest_timestamp:
        query_string['since_last_changed'] = latest_timestamp.isoformat()

    rq = request.Request(f'https://us9.api.mailchimp.com/3.0/lists/{lid}/members?{parse.urlencode(query_string)}',
                         method='GET',
                         headers={'Authorization': authorization})

    results = []
    try:
        with request.urlopen(rq, context=ssl_context.relaxed_context()) as rsp:
            if rsp.getcode() == 200:
                data = json.loads(rsp.read().decode())
                total = data['total_items']

                # only doing here for not returning all the fields in 'merge_fields' in the results
                # as there is no way of asking for members.merge_fields.FNAME or LNAME to limit the returned data
                members = data['members']
                for member in members:
                    merge_fields = member['merge_fields']
                    result = {'id': member['unique_email_id'],
                              'email': member['email_address'],
                              'status': member['status'],
                              'firstname': merge_fields['FNAME'],
                              'lastname': merge_fields['LNAME']}
                    results.append(result)
            else:
                if logging:
                    logging.error('Mailchimp api-read: unexpected response code: %d' % (rsp.getcode(), ))
                return -1, []

    except Exception as e:
        if logging:
            logging.error('Mailchimp api-read: ' + str(e))
        return -1, []

    return total, results
