"""No DNS/HTTP/SMB/FTP/ping calls: every network boundary is mocked."""
import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jsonschema import validate
from modulos import dns_recon, osint, discovery, scanning, banner_grabber, smb_enumerator, bruteforce_ftp, bruteforce_web
import auditoria

SCHEMA = json.loads((ROOT / "docs/schema_resultados.json").read_text(encoding="utf8"))


class ContractTests(unittest.TestCase):
    def check_result(self, result):
        validate(result, SCHEMA)
        return result

    def setUp(self):
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)

    def test_dns_records_mocked(self):
        with patch.object(dns_recon.dns.resolver, "resolve", return_value=[SimpleNamespace(address="192.0.2.1")]):
            result = self.check_result(dns_recon.get_a_records("demo.test"))
        self.assertEqual(result["data"]["A"], ["192.0.2.1"])

    def test_dns_timeout_contract(self):
        with patch.object(dns_recon.dns.resolver, "resolve", side_effect=dns_recon.dns.resolver.Timeout):
            result = self.check_result(dns_recon.get_a_records("demo.test"))
        self.assertEqual(result["status"], "error")

    def test_osint_whois_mocked(self):
        info = SimpleNamespace(registrar="Demo", creation_date=None, expiration_date=None, name_servers=[])
        with patch.object(osint.whois, "whois", return_value=info):
            result = self.check_result(osint.get_whois_data("demo.test"))
        self.assertEqual(result["data"]["registrar"], "Demo")

    def test_osint_search_mocked(self):
        with patch.object(osint, "search", return_value=["https://demo.test/sample"]):
            self.check_result(osint.get_subdomains_via_dorks("demo.test"))
            self.check_result(osint.check_archivos_expuestos("demo.test"))

    def test_discovery_ping_subprocess_mocked(self):
        with patch.object(discovery.platform, "system", return_value="Windows"), patch.object(discovery.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as ping:
            result = self.check_result(discovery.ping_sweep("192.0.2.0/30"))
        self.assertEqual(ping.call_count, 2)
        self.assertEqual(result["data"]["hosts_activos"], ["192.0.2.1", "192.0.2.2"])

    def test_scanning_socket_mocked(self):
        socket = MagicMock()
        socket.__enter__.return_value.connect_ex.return_value = 0
        with patch.object(scanning.socket, "socket", return_value=socket) as factory:
            result = self.check_result(scanning.scan_ports_dispatcher("demo.test", "80,80"))
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(result["data"]["detalles"][0]["estado"], "abierto")
        socket.__exit__.assert_called_once()

    def test_scanning_invalid_input_never_creates_socket(self):
        for ports in ["", "word", "0", "65536", "80,bad", "80,"]:
            with self.subTest(ports=ports), patch.object(scanning.socket, "socket") as factory:
                result = self.check_result(scanning.scan_ports_dispatcher("demo.test", ports))
                self.assertEqual(result["status"], "error")
                factory.assert_not_called()

    def test_socket_context_exits_on_error(self):
        socket = MagicMock()
        socket.__enter__.return_value.connect_ex.side_effect = OSError("synthetic error")
        with patch.object(scanning.socket, "socket", return_value=socket):
            result = self.check_result(scanning.scan_ports_dispatcher("demo.test", "80"))
        self.assertEqual(result["status"], "error")
        socket.__exit__.assert_called_once()

    def test_banner_grabber_socket_mocked(self):
        socket = MagicMock()
        socket.__enter__.return_value.connect_ex.return_value = 0
        socket.__enter__.return_value.recv.return_value = b"HTTP/1.0 200 OK"
        with patch.object(banner_grabber.socket, "socket", return_value=socket):
            result = self.check_result(banner_grabber.BannerGrabber("demo.test", ports=[80]).run())
        self.assertEqual(result["data"]["banners"][0]["status"], "open")

    def test_smb_placeholder_reports_error(self):
        result = self.check_result(smb_enumerator.SMBEnumerator("demo.test").run())
        self.assertEqual(result["status"], "error")

    def test_ftp_boundary_mocked(self):
        with patch.object(bruteforce_ftp.ftplib, "FTP") as factory:
            instance = bruteforce_ftp.FTPBruteForcer("demo.test", max_threads=1)
            instance.load_dictionaries(["synthetic-user"], ["synthetic-password"])
            result = self.check_result(instance.run())
        factory.return_value.connect.assert_called_once()
        self.assertEqual(len(result["data"]["credenciales_encontradas"]), 1)

    def test_web_placeholder_does_not_claim_success(self):
        with self.assertRaises(NotImplementedError):
            bruteforce_web.WebBruteForcer("https://demo.test", {}, "demo").run()

    def test_orchestrator_rejects_invalid_contract(self):
        result = self.check_result(auditoria.ejecutar_modulo(lambda target: {"status":"success"}, "demo.test"))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["grupo"], 0)


if __name__ == "__main__":
    unittest.main()
