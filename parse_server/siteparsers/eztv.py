# ====================================================================================================
#  eztv.py :: siteparser-handler module for TV episode listings on EZTV.ag
# ====================================================================================================
import os
import json
from datetime import datetime
from glob import glob

from bs4 import BeautifulSoup
from pyparsing import alphas, nums, alphanums, Word, Literal, CaselessLiteral, Keyword, Combine, Suppress, ParseResults

from utils.string_utils import human2bytes
from eztv_database import EZTV_Database


def scan_episode_title(title_str, show_title):
    scan_title_str = str(title_str)
    scan_show_title = ''.join(filter(lambda ch: ch not in "():", str(show_title)))

    if not scan_title_str.lower().startswith(scan_show_title.lower()):
        print('*** Show/Title Mismatch! "{}" => {}'.format(title_str, show_title))

    # otherwise, scan title with pyparsing grammar
    extended_info = {}
    scan_title_str = scan_title_str[len(scan_show_title)+1:]

    # define pyparsing grammar
    episode_index = (CaselessLiteral('S') + Word(nums) + CaselessLiteral('E') + Word(nums)).setResultsName('ep_idx')
    res = (Keyword('720p') | Keyword('1080p')).setResultsName('res')
    tv_source = (Keyword('HDTV') | Keyword('WEB')).setResultsName('tv_source')
    distrib = Keyword('[eztv]').setResultsName('distrib')
    flags = (Keyword('PROPER') | Keyword('REPACK')).setResultsName('flags')
    ripper = Combine(Word(alphas) + Literal('264') + Literal('-') + Word(alphanums)).setResultsName('rip_source')
    junk = '...' | CaselessLiteral('CONVERT') | CaselessLiteral('INTERNAL') | CaselessLiteral('REAL')
    title_grammar = episode_index | res | tv_source | distrib | flags | ripper | Suppress(junk)

    # define a parse action that updates our extended_info dictionary
    def update_info(scan_str, pos, tokens):
        name = tokens.getName()
        if name:
            extended_info[name] = tokens[name]
        return ''

    title_grammar.setParseAction(update_info)
    remainder = title_grammar.transformString(scan_title_str).strip()

    # fix episode_index variables
    ep_idx_value = extended_info.get('ep_idx', None)
    if isinstance(ep_idx_value, ParseResults):
        extended_info['ep_idx'] = list(ep_idx_value)

    if remainder and remainder in scan_title_str:
        extended_info['_extra'] = remainder

    # print(extended_info)
    return extended_info


def parse_tvfiles_from_html(html_source):
    """
    parse_tvfiles_from_html() is now a generator function to yield each line of the parsed page,
    for database handling elsewhere.  (This lets us avoid putting EZTV_Database calls in
    this function, and lets this function focus only on parsing.)
    """
    soup = BeautifulSoup(html_source, 'html.parser')
    save_the_date = None

    def parse_date(column_data):
        date_str =  column_data[0].b.text
        datetime_object = datetime.strptime(date_str, '%d, %B, %Y')
        return datetime_object

    def parse_episode_line(column_data):
        show_title = str(column_data[0].find('a').get('title'))
        magnet_tag = column_data[2].find('a', class_='magnet')
        tz_tag = magnet_tag.find_next_sibling('a')

        fs_str = column_data[3].text
        fs_int = 0
        try:
            fs_int = human2bytes(str(fs_str).strip('B'))
        except ValueError:
            pass

        seed_str = column_data[5].text
        num_seeds = int(seed_str.replace(',', '')) if seed_str != '-' else 0

        data = {'show_title': show_title[:-8] if show_title.endswith(' Torrent') else show_title,
                'episode_title': column_data[1].text.strip(),
                'magnet': magnet_tag.get('href'),
                'torrent': tz_tag.get('href') if tz_tag else None,
                'filesize_str': fs_str,
                'filesize_int': fs_int,
                'seeds': num_seeds,
                'eztv_added': save_the_date  # from outer scope
                }

        ext_info = scan_episode_title(data['episode_title'], data['show_title'])
        if ext_info:
            data.update(ext_info)

        return data

    # find H1 tag for the start of the torrent listing
    h1_tag = soup.find('h1')
    h1_tablerow = h1_tag.find_parent('tr')

    # loop through the table rows and match only the show lines
    for row in h1_tablerow.find_next_siblings('tr')[1:]:
        columns = [c for c in row.contents if c != '\n']
        if len(columns) == 1:
            save_the_date = parse_date(columns)
        elif len(columns) == 7:
            episode_data = parse_episode_line(columns)
            yield episode_data


def parse_json(json_data, debug=True):
    print('Received EZTV page:', json_data['page_url'])

    from utils.config import settings
    settings.load_config_module('webparser', 'DevelopmentConfig')

    if debug:  # save output to file, to keep re-parsing during development
        filename = 'eztv_raw.{}.json'.format(datetime.strftime(datetime.now(), '%Y%m%d_%H%M%S'))
        filename = os.path.join(settings.SITEPARSER_eztv.data_dir, filename)
        with open(filename, 'w') as outfile:
            json.dump(json_data, outfile)

    # parse tv_file lines and add each to EZTV_Database
    with EZTV_Database(config=settings) as eztv_db:
        for episode_data in parse_tvfiles_from_html(json_data['page_source']):
            eztv_db.add_tv_file(episode_data)


def parse_raw_file(parse_file=None):

    if parse_file:  # exact file specified
        with open(parse_file, encoding='utf-8') as infile:
            eztv_data = json.load(infile)
            print('+ Parsing page: {}'.format(eztv_data['page_url']))
            parse_eztv_page(eztv_data['page_source'])

    else:  # launch command-line prompt to ask user

        # TODO: Debug why absolute path doesn't work for glob?? => Then use data_dir setting
        """glob_search = '/'.join((settings.SITEPARSER_eztv.data_dir, '*'))"""
        file_list = [f for f in reversed(sorted(glob('../../_data/eztv_*.json')))]
        display_list = [os.path.basename(f) for f in file_list]

        if file_list:
            print('')
            for i, f in enumerate(display_list):
                print('[{}] {}'.format(i+1, f))
            file_index = int(input('    => Select file to parse: ')) - 1  # offset for enumerate() above
            with open(file_list[file_index], encoding='utf-8') as infile:
                eztv_data = json.load(infile)
                print('Parsing page: {}'.format(eztv_data['page_url']))
                parse_eztv_page(eztv_data['page_source'])
        else:
            print('=> No eztv_data files found')


# main() entry point
if __name__ == '__main__':
    from utils.config import settings
    settings.load_config_module('webparser', 'DevelopmentConfig')
    print('settings.SERVER_CONFIG:', settings.SERVER_CONFIG)
    print('settings.SITEPARSER_eztv:', settings.SITEPARSER_eztv.data_dir)
    print('settings.keys:', settings.keys())

    from utils.network_utils import get_net_interfaces
    print('net_ifc:', get_net_interfaces())

    # NEW! Use as ContextManager so that it auto-closes persistent shelves
    with EZTV_Database(config=settings) as eztv_db:

        # print all tv shows-- don't use keys() because they're str().upper()
        for i, v in enumerate(eztv_db.TV_SHOWS.values(), start=1):
            print('    . show {}: {}  => {}'.format(i, v.show_title, v))

        # print all tv_file listings (could use keys(), but not needed)
        for i, v in enumerate(eztv_db.TV_FILES.values(), start=1):
            print('    # {}: {}'.format(i, v))

        # TODO: FIX THIS, with new generator model!
        # TODO: [BROKEN] parse_raw_file(parse_file='../../_data/eztv_data.json')

        # no longer needed... auto-closed by ContextManager
        # eztv_db.close()

