import os
import importlib
from collections import namedtuple

__all__ = ['ConfigBase', 'settings']


class ConfigBase(object):
    """
    The abstract base config model/class from which to inherit other {*Config} classes
    """
    @classmethod
    def set(cls, tuple_name, **kwargs):
        new_tuple = namedtuple(tuple_name, list(kwargs.keys()))
        return new_tuple(**kwargs)


# access manager to dynamically load {*Config} classes
class SettingsManager(object):
    _config_module = None
    _config_class = None
    _app_name = None
    _dir_path = None

    def __getattr__(self, item):
        try:
            return getattr(SettingsManager._config_class, item)
        except AttributeError:
            return None

    @classmethod
    def keys(cls):
        return [v for v in dir(SettingsManager._config_class) if not v.startswith('_') and v != 'set']

    # TODO: Verify specified dir_path & check {env.DIVIA_CONFIG_DIR} setting
    def set_dirpath(dir_path=None):
        pass

    # TODO: user-friendly version with auto-checks for env.vars & dir_path
    def load_config(self):
        pass

    @classmethod
    def load_config_module(cls, app, config):
        module_name = '.'.join(('divia_configs', app))
        cls._config_module = importlib.import_module(module_name)
        if hasattr(cls._config_module, config):
            cls._config_class = getattr(cls._config_module, config)
        else:
            raise Exception('divia_configs.settings: {} not found in {}.'.format(config, module_name))


#
# Instantiate, partly to leverage self.__metaclass__ instead of defining custom
# TODO: look into this later, not sure if this is the best approach.
#
settings = SettingsManager()




class ScratchpadToDeleteLater(object):
    asdf = """
    if app:
        app_name = os.path.splitext(os.path.basename(app))[0]
    else:
        raise Exception('Cannot load Divia settings; {app} not specified in call to load_config().')

    if not config:  # if not manually specified, use required {env} variable
        config = os.getenv('DIVIA_CONFIG_SETTINGS', None)
        if not config:
            raise Exception('Cannot load Divia settings; {env.DIVIA_CONFIG_SETTINGS} not set.')

    divia_config_dir = dir_path or os.getenv('DIVIA_CONFIG_DIR', None) or os.path.expanduser('~/.divia')
    sys.path.insert(0, divia_config_dir)
    # from divia_config.webparser import DevelopmentConfig as Config
    """

    def reload_config(self, app_name=None, config_set=None, base=None):
        """
        Forces a new dynamic module load in the SettingsManager class.  This is always a reload,
        since the original instantiation of SettingsManager will auto-load a Config settings class
        via the required {env.DIVIA_CONFIG_SETTINGS} variable, if not specified in the constructor.
        
        Also allows specifying 'base=__file__' argument, which wouldn't make sense in the constructor,
        since that's called via 'from divia_config import settings' already.
        """
        app = app_name or self.app_name
        if base and not app:
            app = os.path.splitext(os.path.basename(base))[0]
        cfg = config_set or self.config_set
        if not app or not cfg:
            raise Exception('divia_config.settings requires {app_name} and {config_set} to load config.')


