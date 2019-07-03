# -*- coding: utf-8 -*-

import pytest
from os.path import join, dirname
from sanhe_devops_tools.read_json_value import get_json_value

file_path = join(dirname(__file__), "complex-data.json")


def test_get_json_value():
    assert get_json_value(file_path, "name") == "alice"
    assert get_json_value(file_path, "$.name") == "alice"

    assert get_json_value(file_path, "profile.ssn") == "123-45-6789"
    assert get_json_value(file_path, "$.profile.ssn") == "123-45-6789"

    assert get_json_value(file_path, "profile.first name") == "obama"
    assert get_json_value(file_path, "$.profile.first name") == "obama"

    assert get_json_value(file_path, "profile.phone-number") == "999-888-7777"
    assert get_json_value(file_path, "$.profile.phone-number") == "999-888-7777"


if __name__ == "__main__":
    import os

    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])
