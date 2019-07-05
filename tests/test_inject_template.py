# -*- coding: utf-8 -*-

import json
import pytest
from pytest import raises, approx
from sanhe_devops_tools.inject_template import inject_variable, apply_common_tag


def test_inject_variable():
    assert inject_variable(
        "{{ FIRST_NAME }} {{ LAST_NAME }}",
        dict(FIRST_NAME="Obama", LAST_NAME="Barrack"),
    ) == "Obama Barrack"

    with raises(ValueError):
        inject_variable(
            "{{ FIRST_NAME }} {{ LAST_NAME }}",
            dict(FIRST_NAME="Obama")
        )

    with raises(ValueError):
        inject_variable(
            "{{ FIRST_NAME }} {{ LAST_NAME }}",
            dict(LAST_NAME="Obama")
        )

    with raises(ValueError):
        inject_variable(
            "{{ FIRST_NAME }} {{ LAST_NAME }}",
            {"FIRST_NAME }} {{ LAST_NAME": "Obama Barrack"}
        )

def test_apply_common_tag():
    from pprint import pprint

    json_data = json.loads("""
    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "VPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {
                    "CidrBlock": "10.0.0.1:16",
                    "EnableDnsHostnames": true
                }
            },
        }
    }
    """)
    common_tags = [
        {
            "Key": "Name",
            "Value": "my-project",
        },
        {
            "Key": "Stage",
            "Value": "dev",
        }
    ]
    resources_with_common_tags = [
        "AWS::EC2::VPC",
    ]
    pprint(json_data)
    json_data = apply_common_tag(json_data, common_tags, resources_with_common_tags)
    pprint(json_data)




if __name__ == "__main__":
    import os

    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])
