# -*- coding: utf-8 -*-

"""
This script take original cloudformation template, and perform some pre-process,
and derive the final template for deployment. It applies customize logic to avoid
repeat yourself and bring better maintainability.

1. read cloudformation template from json file, strip comment
2. inject variable like ``{{ VAR_NAME }}`` into json text
3. apply common tags to AWS Resource definition
4. generate the final template json file for deployment.
"""

import re
import sys
import json
from os.path import join, dirname, basename, exists, abspath


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


def inject_variable(text, data):
    """
    Read json from ``path``, inject value based on ``data``.

    :type json_str: str
    :param json_str: JSON file body of content

    :type data: dict
    :param path: the key value pairs are the config values defines in ``config.py`` file.

    :rtype: str
    :return: json text
    """
    pattern = r"\{\{([^)]+?)\}\}"  # match pattern ``{{ VAR_NAME }}``

    for var_name in re.findall(pattern, text):
        key = var_name.strip()
        var_name = "{{" + var_name + "}}"
        if key not in data:
            raise ValueError("`{}` not found in config data".format(key, data))
        text = text.replace(var_name, data[key])

    var_name_list = re.findall(pattern, text)
    if len(var_name_list):
        raise ValueError("several VARIABLEs are not evaluated {}".format(var_name_list))

    return text


def apply_common_tag(json_data,
                     common_tags,
                     resources_with_common_tags):
    """
    Apply ``common_tags`` to all AWS Resource that support ``Properties.Tags``.

    The tags explicitly defined in the template overwrite the common_tags.

    :type json_data:
    :param json_data: a dictionary represent cloudformation template data.

    :type common_tags: List[Dict[str, str]]
    :param common_tags: list of tag key value pair, example:
        ``[{"Key": "Name", "Value": "my-project"}, ...]``

    :type resources_with_common_tags: List[str]
    :param resources_with_common_tags: example: ``["AWS::EC2::VPC", ...]``

    :rtype:
    """
    _resources_with_common_tags = set(resources_with_common_tags)
    for r_name, r_data in json_data.get("Resources", dict()).items():
        if r_data["Type"] in _resources_with_common_tags:
            r_properties = r_data["Properties"]
            tag_property_name = "Tags"
            if tag_property_name not in r_properties:
                r_properties[tag_property_name] = common_tags
            else:
                existing_tag_keys = {dct["Key"] for dct in r_properties["Tags"]}
                for dct in common_tags:
                    if dct["Key"] not in existing_tag_keys:
                        r_properties["Tags"].append(dct)


def inject_var_and_apply_tag(tpl_file_path_list):
    """
    Inject variables and apply common tag to list of template file

    :type tpl_file_path_list: List[str]
    :param tpl_file_path_list: list of cloudformation template file
    """
    # Use Shell Script JSON config data
    try:
        config_data = json.loads(strip_comments(read_text(config_object.CONFIG_FINAL_JSON_FILE_FOR_SHELL_SCRIPT)))
    except Exception as e:
        raise ValueError("failed to load json from `{}`".format(config_object.CONFIG_FINAL_JSON_FILE_FOR_SHELL_SCRIPT))

    for p in tpl_file_path_list:
        if not exists(p):
            raise EnvironmentError("'{}' doesn't exists!".format(p))
        json_str = inject_variable_to_cf_template(p, config_data)
        dst_path = join(processed_cloudformation_dir, basename(p))
        try:
            json_data = json.loads(strip_comments(json_str))
        except:
            raise Exception("failed to load json_str from `{}`".format(p))

        try:
            apply_common_tag(json_data, common_tags)
        except:
            raise Exception("failed to apply common tags for `{}`".format(p))

        json_str = json.dumps(json_data, indent=4)
        write_text(json_str, dst_path)


def process_raw_template(origin_master_template_path,
                         processed_cloudformation_dir,
                         var_data,
                         common_tags,
                         resources_with_common_tags):
    """
    It go through all AWS::CloudFormation::Stack, find nested stack template based
    on the relative path defined in TemplateURL, and call
    ``inject_var_and_apply_tag`` function.
    """
    master_tpl_data = json.loads(strip_comments(read_text(origin_master_template_path)))

    template_list = list()
    for r_name, r_data in master_tpl_data.get("Resources", {}).items():
        if r_data["Type"] == "AWS::CloudFormation::Stack":
            relpath = r_data["Properties"]["TemplateURL"]
            nested_stack_template_path = abspath(join(dirname(origin_master_template_path), relpath))
            template_list.append(nested_stack_template_path)

    template_list.append(origin_master_template_path)

    for p in template_list:
        json_str = read_text(p)
        json_str = inject_variable(json_str, var_data)

        dst_path = join(processed_cloudformation_dir, basename(p))
        try:
            json_data = json.loads(strip_comments(json_str))
        except:
            raise Exception("failed to load json_str from `{}`".format(p))

        try:
            apply_common_tag(json_data, common_tags, resources_with_common_tags)
        except:
            raise Exception("failed to apply common tags for `{}`".format(p))

        json_str = json.dumps(json_data, indent=4)
        write_text(json_str, dst_path)


if __name__ == "__main__":
    from config_init import config_object

    here = dirname(__file__)

    # github root directory
    project_root_dir = dirname(here)

    # specify where is the original cloudformation template locate
    origin_cloudformation_dir = join(project_root_dir, "cloudformation", "01-shared-stack")
    origin_master_template_path = join(origin_cloudformation_dir, "99-master.json")
    processed_cloudformation_dir = dirname(__file__)

    # we use Name for display
    # Project to track project cost
    # Stage to specify the dev/test/qa/stage/prod
    # EnvironmentName a common prefix for all AWS resource
    common_tags = [
        {
            "Key": "Name",
            "Value": config_object.ENVIRONMENT_NAME.get_value(),
        },
        {
            "Key": "Project",
            "Value": config_object.PROJECT_NAME_SLUG.get_value(),
        },
        {
            "Key": "Stage",
            "Value": config_object.STAGE.get_value(),
        },
        {
            "Key": "EnvironmentName",
            "Value": config_object.ENVIRONMENT_NAME.get_value(),
        },
    ]

    # These AWS Resource will be associated with common tags
    resource_with_common_tags = [
        "AWS::EC2::VPC",
        "AWS::EC2::Subnet",
        "AWS::EC2::InternetGateway",
        "AWS::EC2::NatGateway",
        "AWS::EC2::RouteTable",
        "AWS::IAM::Role",
        "AWS::EC2::SecurityGroup",
        "AWS::ECS::Cluster",
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
        "AWS::ElasticLoadBalancingV2::TargetGroup",
        "AWS::EC2::Instance",
        "AWS::CloudFormation::Stack",
    ]

    process_raw_template(origin_master_template_path,
                         processed_cloudformation_dir,
                         config_object.to_dict(),
                         common_tags,
                         resource_with_common_tags)
