# -*- coding: utf-8 -*-

"""
A python config management tool to manage config parameter in centralized place.
And allow different devops tools to easily talk to each other via JSON.

This library implemented in pure Python with no dependencies.

The MIT License (MIT)

Copyright 2019 Sanhe Hu <https://github.com/MacHu-GWU>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import print_function
import os
import re
import sys
import json
import inspect
from collections import OrderedDict

if sys.version_info.major >= 3 and sys.version_info.minor >= 5:
    from typing import Dict


def strip_comment_line_with_symbol(line, start):
    """
    Strip comments from line string.
    """
    parts = line.split(start)
    counts = [len(re.findall(r'(?:^|[^"\\]|(?:\\\\|\\")+)(")', part))
              for part in parts]
    total = 0
    for nr, count in enumerate(counts):
        total += count
        if total % 2 == 0:
            return start.join(parts[:nr + 1]).rstrip()
    else:  # pragma: no cover
        return line.rstrip()


def strip_comments(string, comment_symbols=frozenset(('#', '//'))):
    """
    Strip comments from json string.

    :param string: A string containing json with comments started by comment_symbols.
    :param comment_symbols: Iterable of symbols that start a line comment (default # or //).
    :return: The string with the comments removed.
    """
    lines = string.splitlines()
    for k in range(len(lines)):
        for symbol in comment_symbols:
            lines[k] = strip_comment_line_with_symbol(lines[k], start=symbol)
    return '\n'.join(lines)


def read_text(abspath, encoding="utf-8"):
    """
    :type abspath: str
    :type encoding: str
    :rtype: str
    """
    with open(abspath, "rb") as f:
        return f.read().decode(encoding)


def write_text(text, abspath, encoding="utf-8"):
    """
    :type text: str
    :type abspath: str
    :type encoding: str
    :rtype: None
    """
    with open(abspath, "wb") as f:
        return f.write(text.encode(encoding))


def json_dumps(data):
    return json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False)


def add_metaclass(metaclass):
    """
    Class decorator for creating a class with a metaclass.

    This method is copied from six.py
    """

    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)

    return wrapper


class DeriableSetValueError(Exception):
    """
    Raises when trying to set value for Deriable Field.
    """
    pass


#
class Field(object):
    """
    Base class for config value field.

    :type dont_dump: bool
    :param dont_dump: if true, then you can't get the value if ``check_dont_dump = True``
        in :meth:`BaseConfigClass.to_dict` and :meth:`BaseConfigClass.to_json`.
        this prevent from writing sensitive information to file

    :type printable: bool
    :param printable: if False, then it will not be displayed with
        :meth:`BaseConfigClass.pprint`
    """
    _creation_index = 0

    def __init__(self,
                 value=None,
                 default=None,
                 dont_dump=False,
                 printable=True):
        if value is None:
            self.value = default
        self.value = value
        self.dont_dump = dont_dump
        self.printable = printable

        self._config_object = None
        self._creation_index = Field._creation_index
        Field._creation_index += 1

        self._getter_method = None

        def _validate_method(self, value):
            return True

        self._validate_method = _validate_method

    def set_value(self, value):
        raise DeriableSetValueError("Derivable.set_value method should never bee called")

    def get_value(self, check_dont_dump=False, check_printable=False):
        """
        Since the derivable

        :param config_instance:
        :param check_dont_dump:
        :param check_printable:
        :return:
        """
        if self._config_object is None:
            raise AttributeError("Field.get_value() can't be called without "
                                 "initialized with ")
        if check_dont_dump:
            if self.dont_dump:
                raise DontDumpError
        if check_printable:
            if not self.printable:
                return "***HIDDEN***"

        if self._getter_method is None:
            return self.value
        else:
            return self._getter_method(self._config_object)

    def validator(self, method):
        """
        a decorator to bind validate method.

        :type method: callable
        :param method: a callable function like ``method(self, value)``
            that take ``self`` as first parameters representing the config object.
            ``value`` as second parameters to represent the value you want to validate.
        """
        self._validate_method = method

    def validate(self, *args, **kwargs):
        """
        An abstract method executes the validator method.
        """
        raise NotImplementedError


class DontDumpError(Exception):
    """
    Raises when trying to dump a ``dont_dump=True`` config value.
    """
    pass


class Constant(Field):
    """
    Constant Value.
    """

    def set_value(self, value):
        self.value = value

    def validate(self):
        self._validate_method(self, self.get_value())


class Derivable(Field):
    """
    Derivable Value.
    """

    def getter(self, method):
        self._getter_method = method

    def validate(self, config_instance):
        self._validate_method(self, self.get_value(config_instance))


def is_instance_or_subclass(val, class_):
    """Return True if ``val`` is either a subclass or instance of ``class_``."""
    try:
        return issubclass(val, class_)
    except TypeError:
        return isinstance(val, class_)


def _get_fields(attrs, field_class, pop=False, ordered=False):
    """Get fields from a class. If ordered=True, fields will sorted by creation index.
    :param attrs: Mapping of class attributes
    :param type field_class: Base field class
    :param bool pop: Remove matching fields
    """
    fields = [
        (field_name, field_value)
        for field_name, field_value in attrs.items()
        if is_instance_or_subclass(field_value, field_class)
    ]
    if pop:
        for field_name, _ in fields:
            del attrs[field_name]
    if ordered:
        fields.sort(key=lambda pair: pair[1]._creation_index)
    return fields


def _get_fields_by_mro(klass, field_class, ordered=False):
    """Collect fields from a class, following its method resolution order. The
    class itself is excluded from the search; only its parents are checked. Get
    fields from ``_declared_fields`` if available, else use ``__dict__``.
    :param type klass: Class whose fields to retrieve
    :param type field_class: Base field class
    """
    mro = inspect.getmro(klass)
    # Loop over mro in reverse to maintain correct order of fields
    return sum(
        (
            _get_fields(
                getattr(base, "_declared_fields", base.__dict__),
                field_class,
                ordered=ordered,
            )
            for base in mro[:0:-1]
        ),
        [],
    )


class ConfigMeta(type):
    def __new__(cls, name, bases, attrs):
        cls_fields = _get_fields(attrs, Field, pop=False, ordered=True)
        klass = super(ConfigMeta, cls).__new__(cls, name, bases, attrs)
        inherited_fields = _get_fields_by_mro(klass, Field, ordered=True)

        # Assign _declared_fields on class
        klass._declared_fields = OrderedDict(inherited_fields + cls_fields)
        klass._constant_fields = OrderedDict([
            (name, field)
            for name, field in klass._declared_fields.items()
            if isinstance(field, Constant)
        ])
        klass._deriable_fields = OrderedDict([
            (name, field)
            for name, field in klass._declared_fields.items()
            if isinstance(field, Derivable)
        ])
        return klass


class BaseConfigClass(object):
    """

    - :attr:`BaseConfigClass._declared_fields`:
    - :attr:`BaseConfigClass._constant_fields`:
    - :attr:`BaseConfigClass._deriable_fields`:
    """
    _declared_fields = OrderedDict()  # type: Dict[str: Field]
    _constant_fields = OrderedDict()  # type: Dict[str: Constant]
    _deriable_fields = OrderedDict()  # type: Dict[str: Derivable]

    # --- constructuror method
    def __init__(self, **kwargs):
        for name, field in self._declared_fields.items():
            if name in kwargs:
                field.set_value(kwargs[name])
            field._config_object = self

    @classmethod
    def from_dict(cls, dct):
        """
        Only read constant config variables from json file.

        :type dct: dict
        :rtype: BaseConfig
        """
        config = cls()
        for key, value in dct.items():
            if key in config._constant_fields:
                config._constant_fields[key].set_value(value)
        return config

    @classmethod
    def from_json(cls, json_str):
        """
        :type json_str: str
        :rtype: BaseConfig
        """
        return cls.from_dict(json.loads(strip_comments(json_str)))

    def update(self, dct):
        for key, value in dct.items():
            if key in self._constant_fields:
                self._constant_fields[key].set_value(value)

    def update_from_raw_json_file(self):
        dct = json.loads(strip_comments(read_text(self.CONFIG_RAW_JSON_FILE)))
        self.update(dct)

    def to_dict(self, check_dont_dump=True, check_printable=False):
        dct = OrderedDict()
        for attr, value in self._declared_fields.items():
            try:
                dct[attr] = value.get_value(check_dont_dump=check_dont_dump, check_printable=check_printable)
            except DontDumpError:
                pass
            except Exception as e:
                raise e
        return dct

    def to_json(self, check_dont_dump=True, check_printable=False):
        return json.dumps(
            self.to_dict(check_dont_dump=check_dont_dump, check_printable=check_printable),
            indent=4, sort_keys=False,
        )

    def __repr__(self):
        return "Config({})".format(
            self.to_json(check_dont_dump=False, check_printable=True)
        )

    def pprint(self):
        print(self.__repr__())

    def validate(self):
        for attr, value in self._constant_fields.items():
            value.validate()
        for attr, value in self._deriable_fields.items():
            value.validate(self)

    CONFIG_DIR = None

    def _join_config_dir(self, filename):
        if self.CONFIG_DIR is None:
            raise ValueError("You have to specify `CONFIG_DIR`!")
        if not os.path.exists(self.CONFIG_DIR):
            raise ValueError("CONFIG_DIR('{}') doesn't exist!".format(self.CONFIG_DIR))
        return os.path.join(self.CONFIG_DIR, filename)

    @property
    def CONFIG_RAW_JSON_FILE(self):
        return self._join_config_dir("config-raw.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_PYTHON(self):
        return self._join_config_dir("config-final-for-python.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_SHELL_SCRIPT(self):
        return self._join_config_dir("config-final-for-shell-script.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_CLOUDFORMATION(self):
        return self._join_config_dir("config-final-for-cloudformation.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_SAM(self):
        return self._join_config_dir("config-final-for-sam.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_SERVERLESS(self):
        return self._join_config_dir("config-final-for-serverless.json")

    @property
    def CONFIG_FINAL_JSON_FILE_FOR_TERRAFORM(self):
        return self._join_config_dir("config-final-for-terraform.json")

    # --- Custom logic for different devops tools
    def to_python_json_config_data(self):
        return self.to_dict()

    def to_shell_script_config_data(self):
        return self.to_dict()

    def to_cloudformation_config_data(self):
        def to_big_camel_case(text):
            return "".join([
                word[0].upper() + word[1:].lower()
                for word in text.split("_") \
                ])

        return {
            to_big_camel_case(key): value
            for key, value in self.to_dict().items()
        }

    def to_sam_config_data(self):
        return self.to_dict()

    def to_serverless_config_data(self):
        return self.to_dict()

    def to_terraform_config_data(self):
        return self.to_dict()

    #
    def _dump_for_xxx_config_file(self,
                                  to_config_data_meth,
                                  config_json_file_path):
        json_str = json_dumps(to_config_data_meth())
        write_text(json_str, config_json_file_path)

    def dump_python_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_python_json_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_PYTHON,
        )

    def dump_shell_script_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_shell_script_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_SHELL_SCRIPT,
        )

    def dump_cloudformation_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_cloudformation_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_CLOUDFORMATION,
        )

    def dump_sam_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_sam_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_SAM,
        )

    def dump_serverless_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_serverless_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_SERVERLESS,
        )

    def dump_terraform_json_config_file(self):
        self._dump_for_xxx_config_file(
            self.to_terraform_config_data,
            self.CONFIG_FINAL_JSON_FILE_FOR_TERRAFORM,
        )


@add_metaclass(ConfigMeta)
class ConfigClass(BaseConfigClass):
    pass
