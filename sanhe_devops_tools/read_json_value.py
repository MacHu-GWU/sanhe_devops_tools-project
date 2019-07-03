# -*- coding: utf-8 -*-

"""
Echo value in json file. This provide exact same feature for this ``jq`` command,
but it allow comments in JSON::

    $ cat data.json | jq .$AWS_PROFILE -r

Usage::

    $ python read_json_value.py data.json AWS_PROFILE

- arg1: path to the json file
- arg2: json path notation string
"""

import re
import os
import sys
import json


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


def get_json_value(file_path, json_path):
    """
    Read specific field from JSON file.

    :param file_path: the absolute path for a json file
    :param json_path: json path notation.
    """
    # find absolute path
    cwd = os.getcwd()

    if not os.path.isabs(file_path):
        file_path = os.path.abspath(os.path.join(cwd, file_path))

    # fix json_path
    if json_path.startswith("$."):
        json_path = json_path.replace("$.", "", 1)

    with open(file_path, "rb") as f:
        data = json.loads(strip_comments(f.read().decode("utf-8")))

    value = data
    for part in json_path.split("."):
        if part in value:
            value = value[part]
        else:
            raise ValueError("'$.{}' not found in {}".format(json_path, file_path))
    return value


if __name__ == "__main__":
    file_path = sys.argv[1]
    json_path = sys.argv[2]

    value = get_json_value(file_path, json_path)
    print(value)
