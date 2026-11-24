"""Unit tests for subnet.py (standard library only)."""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from subnet import calculate, split

HERE = os.path.dirname(os.path.abspath(__file__))
SUBNET = os.path.join(HERE, "subnet.py")


class CalculateTest(unittest.TestCase):
    def test_slash24_basic(self):
        result = calculate("10.0.50.203/24")
        self.assertEqual(result["network"], "10.0.50.0")
        self.assertEqual(result["prefix"], 24)
        self.assertEqual(result["mask"], "255.255.255.0")
        self.assertEqual(result["wildcard"], "0.0.0.255")
        self.assertEqual(result["broadcast"], "10.0.50.255")
        self.assertEqual(result["first_host"], "10.0.50.1")
        self.assertEqual(result["last_host"], "10.0.50.254")
        self.assertEqual(result["usable_hosts"], 254)
        self.assertEqual(result["total_addresses"], 256)
        self.assertTrue(result["is_private"])

    def test_slash31_rfc3021(self):
        # point-to-point link: both addresses are usable hosts
        result = calculate("192.168.1.14/31")
        self.assertEqual(result["network"], "192.168.1.14")
        self.assertEqual(result["mask"], "255.255.255.254")
        self.assertEqual(result["wildcard"], "0.0.0.1")
        self.assertEqual(result["broadcast"], "192.168.1.15")
        self.assertEqual(result["first_host"], "192.168.1.14")
        self.assertEqual(result["last_host"], "192.168.1.15")
        self.assertEqual(result["usable_hosts"], 2)
        self.assertEqual(result["total_addresses"], 2)
        self.assertTrue(result["is_private"])

    def test_slash32(self):
        result = calculate("10.1.2.3/32")
        self.assertEqual(result["network"], "10.1.2.3")
        self.assertEqual(result["mask"], "255.255.255.255")
        self.assertEqual(result["wildcard"], "0.0.0.0")
        self.assertEqual(result["broadcast"], "10.1.2.3")
        self.assertEqual(result["first_host"], "10.1.2.3")
        self.assertEqual(result["last_host"], "10.1.2.3")
        self.assertEqual(result["usable_hosts"], 1)
        self.assertEqual(result["total_addresses"], 1)
        self.assertTrue(result["is_private"])

    def test_public_network_slash30(self):
        result = calculate("8.8.8.8/30")
        self.assertEqual(result["network"], "8.8.8.8")
        self.assertEqual(result["first_host"], "8.8.8.9")
        self.assertEqual(result["last_host"], "8.8.8.10")
        self.assertEqual(result["broadcast"], "8.8.8.11")
        self.assertEqual(result["usable_hosts"], 2)
        self.assertFalse(result["is_private"])

    def test_host_bits_ignored(self):
        self.assertEqual(
            calculate("10.0.50.200/24")["network"],
            calculate("10.0.50.0/24")["network"],
        )

    def test_invalid_inputs(self):
        for bad in (
            "10.0.0.0",      # no prefix
            "abc/24",        # not an address
            "10.0.0.0/33",   # prefix out of range
            "300.1.1.1/24",  # octet out of range
            "2001:db8::/64", # IPv6 not supported
        ):
            with self.assertRaises(ValueError, msg=bad):
                calculate(bad)


class SplitTest(unittest.TestCase):
    def test_slash24_into_slash26(self):
        self.assertEqual(
            split("10.0.50.0/24", 26),
            ["10.0.50.0/26", "10.0.50.64/26", "10.0.50.128/26", "10.0.50.192/26"],
        )

    def test_split_count_is_power_of_two(self):
        self.assertEqual(len(split("10.0.50.0/24", 28)), 16)

    def test_split_accepts_string_prefix(self):
        self.assertEqual(split("10.0.50.0/24", "/26"), split("10.0.50.0/24", "26"))

    def test_split_from_host_address(self):
        # host bits are masked off: same result as splitting 10.0.50.0/24
        self.assertEqual(split("10.0.50.203/24", 26), split("10.0.50.0/24", 26))

    def test_split_slash31_into_slash32(self):
        self.assertEqual(
            split("192.168.1.0/31", 32),
            ["192.168.1.0/32", "192.168.1.1/32"],
        )

    def test_split_must_produce_smaller_networks(self):
        for cidr, prefix in (
            ("10.0.50.0/24", 24),  # equal prefix
            ("10.0.50.0/24", 20),  # larger network
            ("10.0.50.0/32", 32),  # cannot split a /32
        ):
            with self.assertRaises(ValueError):
                split(cidr, prefix)

    def test_split_invalid_prefix(self):
        for bad in (33, -1, "abc"):
            with self.assertRaises(ValueError):
                split("10.0.50.0/24", bad)


class CliTest(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, SUBNET, *args], capture_output=True, text=True
        )

    def test_cli_calculate(self):
        proc = self._run("10.0.50.203/24")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["network"]["broadcast"], "10.0.50.255")
        self.assertNotIn("split", data)

    def test_cli_split(self):
        proc = self._run("10.0.50.0/24", "--split", "/26")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["split"]["count"], 4)
        self.assertEqual(data["split"]["subnets"][0], "10.0.50.0/26")

    def test_cli_error(self):
        proc = self._run("10.0.0.0/33")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error", proc.stderr)


if __name__ == "__main__":
    unittest.main()
