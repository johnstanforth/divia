# Divia WebParser
# siteparser for: EZTV.ag
import datetime


def parse_json(json_data):
    print('Divia Tracker: {} at {}'.format(json_data['page_url'], datetime.datetime.now()))
