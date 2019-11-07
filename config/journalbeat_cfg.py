#!/usr/bin/python3

import ipaddress
import sys
import yaml

from configobj import ConfigObj
from vrfmanager.vrfmanager import VrfManager
from vyatta import configd

"""
Journalbeat configuration builder for Vyatta vRouter

Copyright (c) 2017-2019, AT&T intellectual property.
All rights reserved.

SPDX-License-Identifier: GPL-2.0-only
"""


JB_PATH = 'system journal export'


def build_journalbeat_options(config):
    """
    Build the config tree for all options under the "journalbeat" branch
    """
    pass


def build_logstash_output(cfg, device_config):
    """
    Build the config tree for all options under the "logstash" branch
    """
    lgstsh_cfg = {}

    build_input_options(cfg, device_config)

    endpoints = device_config['endpoints']
    endpoint_addrs = []
    for endpoint in endpoints:
        fmt_str = "{}:{}"
        try:
            if ipaddress.ip_address(endpoint.get("hostname")).version == 6:
                fmt_str = "[{}]:{}"
        except ValueError:
            # If it's not parsable as an IPv4 or IPv6 address, assume it's a
            # hostname or domain name and pass it though unchanged.
            pass

        endpoint_addrs.append(fmt_str.format(endpoint.get("hostname"),
                                             endpoint.get("port", 5044)))

    lgstsh_cfg["hosts"] = endpoint_addrs
    lgstsh_cfg['index'] = device_config.get('index', 'logstash')

    cfg['output.logstash'] = lgstsh_cfg


def build_logging(config):
    """
    Build the config tree for all options under the "logging" branch
    """
    pass


def build_input_options(cfg, device_config):
    """
    Build the config for input options
    """
    cfg['journalbeat.inputs'] = [{'paths': []}]


def build_options(cfg, device_config):
    """
    Build the config tree for export/output options
    """
    if 'logstash' in device_config.keys():
        build_logstash_output(cfg,
                              device_config.get('logstash', {}))


def write_envfile(vrf_name):
    cfgobj = ConfigObj('/run/journalbeat/journalbeat.env')
    cfgobj["VRF"] = vrf_name
    cfgobj.write()


def get_vyatta_config(configd_client, vrf_manager):
    # Creates journalbeat's YAML-based config and returns this along with
    # routing-instance it's configured under as a tuple
    vrf_name, vyatta_cfg = None, None

    # Find where journalbeat is configured. It will either be under a
    # routing-instance, or under the default system tree. If configuration
    # does not exist at all, we simply exit early and let the wrapper take
    # care of cleaning up and stopping journalbeat.
    for vrf in vrf_manager.get_vrfs():
        ri_path = 'routing routing-instance {} {}'.format(
                vrf.name, JB_PATH)
        if configd_client.node_exists(configd_client.CANDIDATE, ri_path):
            vrf_name = vrf.name
            break  # YANG only allows one instance of journalbeat
    else:
        if configd_client.node_exists(configd_client.CANDIDATE, JB_PATH):
            vrf_name = 'default'

    if vrf_name is None:
        return vrf_name, vyatta_cfg  # None, None

    elif vrf_name != 'default':
        cfg_path = 'routing routing-instance {} {}'
        cfg_path = cfg_path.format(vrf_name, JB_PATH)

    else:
        cfg_path = JB_PATH

    vyatta_cfg = configd_client.tree_get_full_dict(cfg_path)['export']

    return vrf_name, vyatta_cfg


if __name__ == '__main__':
    # Read vyatta config
    configd_client = configd.Client()
    vrf_manager = VrfManager()
    vrf_name, vyatta_cfg = get_vyatta_config(configd_client, vrf_manager)

    if vrf_name is None or not vyatta_cfg:
        sys.exit(-1)  # Nothing configured, wrapper will shutdown JB

    jb_cfg = {}
    build_options(jb_cfg, vyatta_cfg)

    with open('/etc/journalbeat.yml', 'w') as config_file:
        yaml.dump(jb_cfg, config_file, default_flow_style=False)
    write_envfile(vrf_name)
