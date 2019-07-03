# -*- coding: utf-8 -*-

import pytest
from os.path import join, dirname
from sanhe_devops_tools.get_cf_parameter_overrides import get_parameters_data

template_path = join(dirname(__file__), "master-tier.json")
json_file = join(dirname(__file__), "master-tier-config.json")


def test_get_parameters_data():
    parameters = get_parameters_data(template_path, json_file)
    assert parameters == {"ProjectName": "config_lib", "Stage": "dev"}


if __name__ == "__main__":
    import os

    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])
