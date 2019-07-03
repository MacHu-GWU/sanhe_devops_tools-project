# -*- coding: utf-8 -*-

"""
This script generate required parameters syntax as string for
``aws cloudformation deploy ... --parameter-overrides param1=value1 param2=value2 ...`` command.
    
**How to Use**:

**Syntax**:

.. code-block:: bash

    $ python <path-to>/get_cf_parameter_overrides.py <cloudformation-template-json-file> <config-data-json-file>

Example:

.. code-block:: bash

    $ python ./devops/get_cf_parameter_overrides.py vpc-tier.json config-final-for-cloudformation.json
    EnvironmentName=urmtc-dev SubnetPrivate1CIDR=10.53.3.0/24 ...
"""

import re
import os
import json
from os.path import join, abspath, isabs
from collections import OrderedDict


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


def read_json_data(file):
    with open(file, "rb") as f:
        return json.loads(strip_comments(f.read().decode("utf-8")))


def get_parameters_data(template_path, json_file):
    cwd = os.getcwd()

    if not isabs(template_path):
        template_path = abspath(join(cwd, template_path))

    if not isabs(json_file):
        json_file = abspath(join(cwd, json_file))

    required_parameters = list(
        read_json_data(
            template_path
        ).get("Parameters", dict()).keys()
    )
    full_cloudformation_parameter_data = read_json_data(json_file)

    parameters = OrderedDict()
    for key in required_parameters:
        if key in full_cloudformation_parameter_data:
            parameters[key] = full_cloudformation_parameter_data[key]
        else:
            raise ValueError("Parameter '{}' from {} not found in {}".format(
                key, template_path, json_file
            ))
    return parameters


if __name__ == "__main__":
    import sys

    template_path = sys.argv[1]
    json_file = sys.argv[2]

    parameters = get_parameters_data(template_path, json_file)

    chunks = list()
    for key, value in parameters.items():
        arg = "{}={}".format(key, value)
        chunks.append(arg)

    arg = " ".join(chunks)
    print(arg)
