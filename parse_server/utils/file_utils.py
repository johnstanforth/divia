import os


def expand_filename(*args, **kwargs):
    # print("\t\t\t[expand_fn.start]:", vars())
    filename = args[0] if args else (kwargs.get('filename', None) or kwargs.get('file', None))

    dir_path = kwargs.get('dir_path', None)
    env_file = kwargs.get('env_file', None)
    env_dir = kwargs.get('env_dir', None)
    env_filename = os.getenv(env_file, None) if env_file else None
    env_dir_path = os.getenv(env_dir, None) if env_dir else None

    # directly-specified vars take precedence over environment vars
    my_file = filename or env_filename
    my_dir = dir_path or env_dir_path or os.getcwd()  # so by defn, is never None

    try:  # support user-path expansion
        my_file = os.path.expanduser(my_file) if my_file.startswith('~') else my_file
    except AttributeError:
        raise Exception('expand_filename(): {filename} and {env_file} cannot BOTH be None')

    my_dir = os.path.expanduser(my_dir) if my_dir.startswith('~') else my_dir

    # then lastly, support dir_path
    final_answer = os.path.join(my_dir, my_file)
    # print("\t\t\t[expand_fn.end]:", vars())

    return final_answer
