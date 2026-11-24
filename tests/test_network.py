import unittest

import network


class NetworkHelpersTest(unittest.TestCase):
    def test_parse_ports_single_and_ranges(self):
        self.assertEqual(network.parse_ports("22,80,443,8000-8002"),
                         [22, 80, 443, 8000, 8001, 8002])

    def test_parse_ports_sorts_and_deduplicates(self):
        self.assertEqual(network.parse_ports("443,80,443,81-82"),
                         [80, 81, 82, 443])

    def test_parse_ports_rejects_invalid_range(self):
        with self.assertRaises(ValueError):
            network.parse_ports("90-20")

    def test_parse_ports_enforces_scan_limit(self):
        with self.assertRaises(ValueError):
            network.parse_ports("1-5000")

    def test_nmcli_escaped_colons(self):
        parsed = network._split_nmcli_row(r"Cafe:Guest:AA\:BB\:CC:11:72:WPA2")
        self.assertEqual(parsed[0], "Cafe")
        self.assertEqual(parsed[1], "Guest")
        self.assertEqual(parsed[2], "AA:BB:CC")

    def test_locally_administered_mac_vendor(self):
        self.assertEqual(network._vendor("02:11:22:33:44:55"), "Rastgele/yerel MAC")

    def test_known_vendor(self):
        self.assertEqual(network._vendor("00:1A:11:AA:BB:CC"), "Google")


if __name__ == "__main__":
    unittest.main()
