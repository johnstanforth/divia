import json
import os

from datetime import datetime


def parse_json(json_data, debug=True):
    print('Divia Tracker: {} at {}'.format(json_data['page_url'], datetime.now()))

    if debug:  # save output to file, to keep re-parsing during development
        filename = 'divia_tracker_raw.{}.json'.format(datetime.strftime(datetime.now(), '%Y%m%d_%H%M%S'))
        filename = os.path.join('../_data', filename)
        with open(filename, 'w') as outfile:
            json.dump(json_data, outfile)


