# ====================================================================================================
#  tv_movie_info.py :: utility functions to access TV & Movie info via The Movie Database API
# ====================================================================================================
import tmdbsimple as tmdb


def test_movie_search(search_str):
    movie = tmdb.Movies(603)
    response = movie.info()
    print(movie.title)


def tv_search(search_str):
    search = tmdb.Search()
    response = search.tv(query=search_str)
    for s in search.results:
        print(s)


# main() entry point
if __name__ == '__main__':
    from utils.config import settings
    settings.load_config_module('webparser', 'DevelopmentConfig')
    print('settings.keys:', settings.keys())
    print('settings.tmdb:', settings.THE_MOVIE_DATABASE_API_KEY)
    tmdb.API_KEY = settings.THE_MOVIE_DATABASE_API_KEY

    # test_movie_search('asdf')

    tv_search('Game of Thrones')

