#!/usr/bin/env python3

from unittest import TestCase
from unittest.mock import Mock, patch
import collections


MockVrf = collections.namedtuple('MockVrf', "name")


class MockVyattaConfigdClient:

    CANDIDATE = 2

    def __init__(self, jb_path=None, cfg=None):
        self.jb_path = jb_path
        self.cfg = cfg

    def tree_get_full_dict(self, path):
        if path == self.jb_path:
            return self.cfg

    def node_exists(self, db, path):
        return path == self.jb_path


class MockVyattaVrfManager:
    def __init__(self, vrfs=None):
        self.vrfs = [] if vrfs is None else vrfs

    def get_vrfs(self):
        return self.vrfs


class TestJournalbeatConfigBase(TestCase):

    def setUp(self):
        mocked_modules = {"vyatta": Mock(),
                          "vrfmanager.vrfmanager": Mock()}
        patch.dict('sys.modules', mocked_modules).start()

        from config.journalbeat_cfg import get_vyatta_config as _get_vyatta_cfg
        self.get_vyatta_config = _get_vyatta_cfg

        self.configd_client = MockVyattaConfigdClient({})
        self.vrf_manager = MockVyattaVrfManager()

    def tearDown(self):
        pass


class TestDeterminingConfigLocation(TestJournalbeatConfigBase):

    def test_no_config(self):
        vrf_name, vyatta_cfg = self.get_vyatta_config(
                self.configd_client, self.vrf_manager)

        self.assertIsNone(vrf_name)
        self.assertIsNone(vyatta_cfg)

    def test_default_ri_config(self):
        cfg = {"export": {"logstash": 'some_cfg'}}
        self.configd_client.jb_path = 'system journal export'
        self.configd_client.cfg = cfg

        vrf_name, vyatta_cfg = self.get_vyatta_config(
                self.configd_client, self.vrf_manager)

        self.assertEqual('default', vrf_name)
        self.assertEqual(cfg['export'], vyatta_cfg)

    def test_ri_config(self):
        ri_name = 'att-mgmt'
        path = f'routing routing-instance {ri_name} system journal export'
        cfg = {"export": {"logstash": 'cfg_thats_not_important_for_this_test'}}
        self.configd_client.jb_path = path
        self.configd_client.cfg = cfg
        self.vrf_manager.vrfs.append(MockVrf(name=ri_name))

        vrf_name, vyatta_cfg = self.get_vyatta_config(
                self.configd_client, self.vrf_manager)

        self.assertEqual(ri_name, vrf_name)
        self.assertEqual(cfg['export'], vyatta_cfg)


class TestExportOptions(TestJournalbeatConfigBase):

    def test_full_tree(self):
        from config.journalbeat_cfg import build_options
        device_cfg = {
            "logstash": {
                "endpoints": [
                    {
                        "endpoint": "one",
                        "hostname": "hostname1",
                    },
                    {
                        "endpoint": "two",
                        "hostname": "hostname2",
                        "port": 54321,
                    },
                ],
                "index": "over-here",
            },
        }

        output_cfg = {}

        expected_cfg = {
            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "hosts": ["hostname1:5044", "hostname2:54321"],
                "index": "over-here",
            },
        }

        build_options(output_cfg, device_cfg)

        self.assertDictEqual(output_cfg, expected_cfg)


class TestInputOptions(TestJournalbeatConfigBase):

    def test_defaults(self):
        from config.journalbeat_cfg import build_input_options

        output_cfg = {}
        device_cfg = {}
        expected_cfg = {
            "journalbeat.inputs": [
                {'paths': []},
            ],
        }

        build_input_options(output_cfg, device_cfg)

        self.assertEqual(expected_cfg, output_cfg)


class TestOutputLogstashConfig(TestJournalbeatConfigBase):

    def test_simple_hostname(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "hostname_1",
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["hostname_1:5044"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_simple_ipv4(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint",
                    "hostname": "192.168.1.1",
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ['192.168.1.1:5044'],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_simple_ipv6(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "fe80::1",
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["[fe80::1]:5044"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_simple_hostname_alt_port(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "hostname_1",
                    "port": 5049,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["hostname_1:5049"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_simple_ipv4_alt_port(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "192.168.1.1",
                    "port": 5049,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["192.168.1.1:5049"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_simple_ipv6_alt_port(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "fe80::1",
                    "port": 5049,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["[fe80::1]:5049"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEqual(expected_cfg, output_cfg)

    def test_multi_hostnames(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "hostname_1",
                },
                {
                    "endpoint": "endpoint_2",
                    "hostname": "hostname_2",
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["hostname_1:5044", "hostname_2:5044"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_multi_hostnames_and_ports(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "hostname_1",
                    "port": 5045,
                },
                {
                    "endpoint": "endpoint_2",
                    "hostname": "hostname_2",
                    "port": 5046,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["hostname_1:5045", "hostname_2:5046"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_multi_ipv4s_and_ports(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "192.168.1.1",
                    "port": 5045,
                },
                {
                    "endpoint": "endpoint_2",
                    "hostname": "192.168.1.2",
                    "port": 5046,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["192.168.1.1:5045", "192.168.1.2:5046"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_multi_ipv6s_and_ports(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "fe80::1",
                    "port": 5045,
                },
                {
                    "endpoint": "endpoint_2",
                    "hostname": "fe80::2",
                    "port": 5046,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ["[fe80::1]:5045", "[fe80::2]:5046"],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)

    def test_multi_mixed_and_ports(self):
        from config.journalbeat_cfg import build_logstash_output

        output_cfg = {}
        input_cfg = {
            "endpoints": [
                {
                    "endpoint": "endpoint_1",
                    "hostname": "192.168.1.1",
                    "port": 5045,
                },
                {
                    "endpoint": "endpoint_2",
                    "hostname": "fe80::2",
                    "port": 5046,
                },
                {
                    "endpoint": "endpoint_3",
                    "hostname": "hostname_3",
                    "port": 5047,
                },
            ]
        }
        expected_cfg = {

            "journalbeat.inputs": [
                {'paths': []},
            ],
            "output.logstash": {
                "index": "logstash",
                "hosts": ['192.168.1.1:5045',
                          "[fe80::2]:5046",
                          'hostname_3:5047'],
            }
        }

        build_logstash_output(output_cfg, input_cfg)

        self.assertEquals(expected_cfg, output_cfg)
