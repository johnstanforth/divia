import json
import os
import shelve


# -------------------------------------------------------------------
#  Schema for database objects (stored in shelves)
# -------------------------------------------------------------------
class TV_Show(object):
    def __init__(self, title):
        self.show_title = title
        self.season_set = set()         # set of seasons (by int)
        self.episodes = {}              # key=(S01, E01), value=TV_Show_Episode
        self.is_subscribed = False      # supports TV_Show subscription (to auto-download)
        self.is_on_watchlist = False    # TODO: Flag certain shows to show in Watchlist (to *maybe* download)

    def __repr__(self):
        return 'seasons={season_set}, episodes={episodes}, subscribed={is_subscribed}'.format_map(self.__dict__)


class TV_Show_Episode(object):
    def __init__(self, season_num, episode_num):
        self.episode_id = (season_num, episode_num)  # (S01, E01) tuple, also used as key for {TV_Show.episodes}
        self.episode_title = None
        self.show_title = None                      # repeating here just for future safety and convenience
        self.file_list = []                         # list of matching TV_File filenames (NOT object references)
        self.is_downloaded = False
        self.is_viewed = False
        self.is_deleted = False

    def __repr__(self):
        if self.episode_title:
            return 'Episode[S{0:0>2}E{0:0>2}: "{}"]'.format(self.episode_id[0],
                                                            self.episode_id[1],
                                                            self.episode_title)
        else:
            return 'Episode[S{0:0>2}E{0:0>2}]'.format(self.episode_id[0],
                                                      self.episode_id[1])

    def __details__(self):
        if self.episode_title:
            return 'Episode[ {episode_id: "{episode_title}", file_list={file_list} ]'.format_map(self.__dict__)
        else:
            return 'Episode[ {episode_id, file_list={file_list} ]'.format_map(self.__dict__)


class TV_File(object):
    def __init__(self, filename):
        self.filename = filename
        self.file_info = {}
        self.resolution = None          # TODO: {'480p', '720p', '1080p', '2160p'}
        self.res_lines_int = 0          # TODO: {480, 720, 1080, 2160}
        self.queue_for_download = False
        self.is_downloaded = False
        self.is_deleted = False

    def __repr__(self):
        return 'TV_File[ "{filename}", res={resolution} ]'.format_map(self.__dict__)

# -------------------------------------------------------------------


# class to encapsulate all EZTV tv show logic & persistence
class EZTV_Database(object):

    def __init__(self, config=None):
        self.settings = config
        self.dir_path = '../_data'  # MANUAL DEFINE FOR NOW
        self.TABLES = {'EZTV_DATA_OBJECTS', 'TV_SHOWS', 'TV_FILES'}
        self.setup_databases()

    # helper function to streamline creation of multiple shelves
    def open_shelf(self, db_name):
        # TODO: Why are absolute paths not working???
        #dir_path = self.settings.SITEPARSER_eztv.data_dir
        return shelve.open(os.path.join(self.dir_path, db_name), protocol=4, writeback=True)

    def load_eztv_data_object(self, object_name, default=None):
        try:
            obj = self.EZTV_DATA_OBJECTS[object_name]
            setattr(self, object_name, obj)
        except KeyError:
            if default:
                self.EZTV_DATA_OBJECTS[object_name] = default
                setattr(self, object_name, self.EZTV_DATA_OBJECTS[object_name])

    def save_eztv_data_object(self, object_name):
        self.EZTV_DATA_OBJECTS[object_name] = getattr(self, object_name)

    def setup_databases(self):
        for table_name in self.TABLES:
            table_filename = 'db_' + table_name.lower()
            table_ptr = self.open_shelf(table_filename)
            setattr(self, table_name, table_ptr)
            print('- db_shelf "{}" now online: file "{}"'.format(table_name, table_filename))

        # loads custom data objects from db_shelf
        self.load_eztv_data_object('shows_subscribed', default=set())
        self.load_eztv_data_object('shows_on_watchlist', default=set())

    def close(self):
        for table_name in self.TABLES:  # loop through and close() all shelves!
            if hasattr(self, table_name) and getattr(self, table_name, None):
                getattr(self, table_name).close()
        print('- db_shelves closed')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def find_tv_show(self, show_title, create_new=True):
        tvshow_key = str(show_title).upper()
        try:
            return (True, self.TV_SHOWS[tvshow_key])
        except KeyError:
            if create_new:
                new_show = TV_Show(show_title)
                self.TV_SHOWS[tvshow_key] = new_show
                print('+ added new tv_show:', new_show.show_title)
                if tvshow_key in self.shows_subscribed:  # support pre-existing TV_Show subscriptions
                    new_show.is_subscribed = True
                    print('  - Subscription found for "{}"... SUBSCRIBED'.format(new_show.show_title))
            else:
                new_show = None
            return (False, new_show)

    def find_show_episode(self, show_object, season_num, episode_num):
        # REQUIRES show_object (from find_tv_show() above)
        try:
            return (True, show_object.episodes[(season_num, episode_num)])
        except KeyError:
            new_episode = TV_Show_Episode(season_num, episode_num)
            new_episode.show_title = show_object.show_title  # for safety, this should ONLY ever be defined here
            show_object.episodes[(season_num, episode_num)] = new_episode
            print('+ added new tv_show_episode:', new_episode.show_title, new_episode.__repr__())
            return (False, new_episode)

    def find_tv_file(self, file_info):
        filename = file_info['torrent'].split('/')[-1] if file_info['torrent'] else file_info['episode_title']
        if str(filename).endswith('.torrent'):
            filename = filename[0:-8]
        try:
            return (True, self.TV_FILES[filename])
        except KeyError:
            new_tv_file = TV_File(filename)
            new_tv_file.file_info.update(file_info)
            self.TV_FILES[filename] = new_tv_file
            print('+ added new tv_file:', new_tv_file.filename)
            return (False, new_tv_file)

    def add_tv_file(self, file_info):
        show = self.find_tv_show(file_info['show_title'])[1]
        if 'ep_idx' in file_info:
            season_num = int(file_info['ep_idx'][1])
            show.season_set.add(season_num)
            ep_number = int(file_info['ep_idx'][3])
            episode = self.find_show_episode(show, season_num, ep_number)[1]

            is_exists, tv_file = self.find_tv_file(file_info)
            if not is_exists:  # just created, not pre-existing
                episode.file_list.append(tv_file.filename)
                if show.is_subscribed:  # support TV_Show subscriptions!
                    print('  - found subscription for:', show.show_title)
                    self.queue_tv_file_download(tv_file)
                return True  # inversion: add_tv_file() is True if just added

            print('- found tv_file already previously indexed:', tv_file.filename)
            return False  # NOT created, because we found pre-existing file

    def queue_tv_file_download(self, tv_file):
        with open(os.path.join(self.dir_path, 'download_queue.txt'), 'a') as queue_file:
            queue_file.write(tv_file.file_info['torrent'])
            queue_file.write('\n')
            tv_file.queue_for_download = True
            print('  - queued tv_file "{}" for download'.format(tv_file.filename))

    def update_show_subscriptions(self, json_file=None):
        if not json_file:
            json_file = os.path.join(self.dir_path, 'show_subscriptions.json')

        with open(json_file, encoding='utf-8') as infile:
            subscription_data = json.load(infile)
            print('+ Processing "shows_subscribed" from {}...'.format(json_file))
            for show_name in subscription_data['shows_subscribed']:
                self.shows_subscribed.add(str(show_name).upper())
                # TODO: This wll add/update the dbshelf, but need different way to *remove* subscription
                found, tv_show = self.find_tv_show(show_name, create_new=False)
                if found and not tv_show.is_subscribed:
                    tv_show.is_subscribed = True
                    print('  - Subscribed to show "{}"'.format(tv_show.show_title))
                elif not found:
                    print('  - Warning: Subscription to "{}" IGNORED... TV_Show not found'.format(show_name))

        self.save_eztv_data_object('shows_subscribed')
