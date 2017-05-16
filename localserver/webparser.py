#!/usr/bin/env python3.6
import os
import importlib
import json
import re

import bottle
import sys

bottle.BaseRequest.MEMFILE_MAX = 10 * 1024 * 1024  # 10MB in bytes
from bottle import route, run, template, get, post, request


# function to programmatically load siteparser modules as URL handlers
def load_siteparsers_map():
    with open('./siteparsers/siteparsers.json', encoding='utf-8') as config_file:
        config_data = json.load(config_file)

    # parse JSON config file to dynamically import handler modules
    siteparsers_map = {}
    for url_match, handler in config_data.items():
        module_name = 'siteparsers.' + os.path.splitext(handler['parser'])[0]
        siteparsers_map[url_match] = importlib.import_module(module_name)


    LATER_OPTIMIZATION_COMPILE_REGEXP_AND_ADD_PREFIX_POSTFIX_FOR_FULLMATCH = """
    dicti = {'the': 20, 'a': 10, 'over': 2}
    patterns = ['the', 'an?']
    regex_matches = [re.compile("^" + pattern + "$").match for pattern in patterns]

    extractddicti = {k: v for k, v in dicti.items()
                     if any(regex_match(k) for regex_match in regex_matches)}
    """

    return siteparsers_map


SITEPARSERS_MAP = load_siteparsers_map()


@route('/hello/<name>')
def index(name):
    return template('<b>Hello {{name}}</b>!', name=name)


@get('/webparser')
def webparser_info():
    return '''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    '''


@post('/webparser')
def parse_webpage():
    data = request.json
    for regex, handler in SITEPARSERS_MAP.items():
        if re.search(regex, data['page_url']):
            handler.parse_json(data)

    return json.dumps({'success': True})


# main() entry point
if __name__ == '__main__':
    from utils.config import settings
    settings.load_config_module('webparser', 'DevelopmentConfig')

    srv = settings.LocalServer
    run(host=srv.host, port=srv.port)
