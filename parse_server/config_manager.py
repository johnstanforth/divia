import json

from utils.file_utils import expand_filename

__all__ = ['ConfigBase']


# base node for new ConfigTree
class ConfigNode(object):
    def __init__(self, name=None, value=None, node_type=0):
        self._superset('_name', name)
        self._superset('_value', value)
        self._superset('_node_type', node_type)  # 0=None/default ... 1=assigned

    def __len__(self):
        return len([k for k in self.__dict__.keys() if not k.startswith('_')])

    def _superset(self, attr, value):
        super().__setattr__(attr, value)

    def find_subnode(self, item):
        node_ptr = self
        for segment in item.split('.'):
            node_ptr = getattr(node_ptr, segment)
        return node_ptr

    def __getattr__(self, item):
        if '.' in item:
            subnode = self.find_subnode(item)
            return subnode
        # print('\t[{}] creating new node: {!r}'.format(self._name, item))
        self._superset(item, ConfigNode(name=item))
        return getattr(self, item)

    def __setattr__(self, attr, value):
        # print("\t[{}] setting {!r} to {!r}".format(self._name, attr, value))
        if isinstance(value, dict):
            subnode = getattr(self, attr)  # will auto-create if not exist
            if '_' in value:  # if the sub-dict contains a magic key called '_'
                subnode._superset('_value', value.pop('_'))
            for k, v in value.items():
                setattr(subnode, k, v)  # recursive assignment
        else:
            subnode = getattr(self, attr)  # will auto-create if not exist
            subnode._superset('_value', value)
            subnode._superset('_node_type', 1)

    def as_dict(self, recursive=False, _values=False):
        if recursive:
            var_dict = {}
            for k, v in self.__dict__.items():
                if isinstance(v, ConfigNode):
                    if len(v) == 0 and not _values:
                        var_dict[k] = v._value
                    else:
                        var_dict[k] = v.as_dict(recursive=recursive, _values=_values)
                        if _values or v._value:
                            var_dict[k]['_'] = v._value

                elif not k.startswith('_'):
                    var_dict[k] = v
        else:
            if _values:
                var_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
                var_dict['_'] = self._value
            else:
                var_dict = {k: v._value for k, v in self.__dict__.items() if not k.startswith('_')}
        return var_dict

    def __call__(self, *args, **kwargs):
        if kwargs.get('as_dict', False):
            return {varname: getattr(self, varname)._value for varname in args} if len(args) else self.as_dict()
        # otherwise, return a list of args, or a single _value
        return [getattr(self, varname)._value for varname in args] if len(args) else self._value

    def __getitem__(self, item):
        # print("\t[{}] getting item for {!r}".format(self._name, item))
        return getattr(self, item)._value

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __delitem__(self, key):
        if not str(key).startswith('_'):
            delattr(self, key)
        else:
            raise Exception('ConfigNode: Cannot delete protected variable {!r}'.format(key))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __repr__(self):
        return 'ConfigNode(name="{_name}", value="{_value}", type="{_node_type}")'.format_map(self.__dict__)


class ConfigManager(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            return cls._instance
        else:
            inst = cls._instance = super(ConfigManager, cls).__new__(cls, *args, **kwargs)
            return inst

    @classmethod
    def _load_dict(cls, parse_dict, node=None, root_name=None):
        if node is None:
            node = ConfigNode(root_name) if root_name else ConfigNode()
        for k, v in parse_dict.items():
            setattr(node, k, v)
        return node

    @classmethod
    def _load(cls, load_src, *args, **kwargs):
        if isinstance(load_src, dict):
            cls._load_dict(load_src, *args, **kwargs)

    @classmethod
    def _save_json(cls, root_node, *args, **kwargs):
        filename = expand_filename(**kwargs)
        if not filename:
            raise Exception('ConfigManager._save_json(): Invalid filename')

        with open(filename, 'w') as write_config_file:
            tree_copy = root_node.as_dict(recursive=True, _values=False)
            json.dump(tree_copy, write_config_file, sort_keys=True, indent=4, separators=(',', ': '))

    @classmethod
    def __autoload_parse_dict(cls, target_node, *args, **kwargs):
        cfg_object = kwargs.pop('_config_object')

        def process_args(arg_list):
            for src_var in arg_list:
                if isinstance(src_var, list) or isinstance(src_var, tuple):
                    process_args(src_var)
                elif isinstance(src_var, str):
                    if hasattr(cfg_object, src_var):
                        load_object = getattr(cfg_object, src_var)
                        if isinstance(load_object, dict):
                            cls._load_dict(load_object, node=target_node)

        if args:
            process_args(args)

        if kwargs:
            cls._load_dict(kwargs, node=target_node)

    @classmethod
    def __autoload_parse_json(cls, target_node, *args, **kwargs):

        def load_json_file(fn=None):
            filename = expand_filename(**kwargs, filename=fn) if fn else expand_filename(**kwargs)
            with open(filename, 'r') as json_file:
                json_data = json.load(json_file)
                cls._load_dict(json_data, node=target_node)

        for fn in args:
            load_json_file(fn)

        if 'file' in kwargs:
            load_json_file(kwargs.pop('file'))

        if 'filename' in kwargs:
            load_json_file(kwargs.pop('filename'))

        if 'files' in kwargs:
            if not isinstance(kwargs.get('files'), list) and not isinstance(kwargs.get('files'), tuple):
                raise Exception('__autoload_parse_json(): {files} keyword arg must be LIST or TUPLE only')
            for fn in kwargs.pop('files'):
                load_json_file(fn)

    @classmethod
    def _autoload_config_data(cls, config_object):
        fn_map = {'dict': cls.__autoload_parse_dict,
                  'json': cls.__autoload_parse_json,}
        for load_call in config_object.__load__:
            scope, fn_type, *args = load_call
            kwargs = {}
            for i, item in enumerate(args):
                if isinstance(item, dict):
                    kwargs = args.pop(i)

            kwargs['_config_object'] = config_object
            target_node = getattr(config_object._root_node, scope) if scope else config_object._root_node
            fn_map[fn_type](target_node, *args, **kwargs)


class ConfigMetaRegister(type):
    _instances = {}
    # TODO: Idea==> maybe have a dict that maps ROOT for each to a shelve'd .root_node entry, and reloads data?
    # TODO: Otherwise, we can parse from a config file (JSON?) to load?

    # TODO: Idea==> ContextManager will work if we just load quickly, deepycopy data, then save/close
    # TODO: Should do something to manually writeback changes when we want (separate from close-- like, reopen to save)

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # print('***Creating NEW:', cls)
            cls._instances[cls] = super(ConfigMetaRegister, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    def __new__(cls, *args, **kwargs):
        args[2]['_cfg_mgr'] = ConfigManager()  # inject a ConfigManager for each Config class
        args[2]['_config_class'] = args[2]['__qualname__']
        # print('***[ConfigMetaRegister]***', args, kwargs)
        return type.__new__(cls, *args, **kwargs)


class ConfigBase(metaclass=ConfigMetaRegister):
    def __init__(self):
        self._superset('_root_node', ConfigNode(name='[ROOT].{}'.format(self._config_class)))
        self._cfg_mgr._autoload_config_data(self)

    def _superset(self, attr, value):
        super().__setattr__(attr, value)

    def __getattr__(self, item):
        return getattr(self._root_node, item)

    def as_dict(self, recursive=True, _values=False):
        return self._root_node.as_dict(recursive=recursive, _values=_values)

    def as_pprint(self):
        dict_copy = self.as_dict(recursive=True, _values=False)
        return json.dumps(dict_copy, sort_keys=True, indent=4, separators=(',', ': '))

    def __setattr__(self, key, value):
        # print("\t[cbase] setting {!r} to {!r}".format(key, value))
        self._superset(key, value)

    def save_json(self, *args, **kwargs):
        return self._cfg_mgr._save_json(self._root_node, *args, **kwargs)

    def _load(self, *args, **kwargs):
        return self._cfg_mgr._load(*args, **kwargs)

