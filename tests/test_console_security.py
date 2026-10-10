import base64
import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import helpers  # noqa: F401  (puts console/ on sys.path)
import container_server as cs
import security

JSON = {"Content-Type": "application/json"}


class GuardUnitTest(unittest.TestCase):
    def test_host_names(self):
        for host in ("localhost:8766", "127.0.0.1", "[::1]:8766", "192.168.1.20:8766", "ai-console"):
            self.assertTrue(security.host_allowed(host), host)
        for host in ("evil.example", "evil.example:8766", "", None, "localhost.evil.example"):
            self.assertFalse(security.host_allowed(host), host)
        self.assertTrue(security.host_allowed("lab.lan:8766", security.parse_hosts("Lab.LAN, other")))

    def test_post_rules(self):
        base = {"Host": "127.0.0.1:8766", "Content-Type": "application/json"}
        self.assertIsNone(security.check("POST", "/api/start", base))
        self.assertIsNone(security.check("POST", "/api/start", {**base, "Origin": "http://127.0.0.1:8766"}))
        self.assertEqual(security.check("POST", "/api/start", {**base, "Origin": "http://evil.example"})[0], 403)
        self.assertEqual(security.check("POST", "/api/start", {**base, "Origin": "null"})[0], 403)
        self.assertEqual(security.check("POST", "/api/start", {**base, "Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(security.check("POST", "/api/start", {"Host": base["Host"], "Content-Type": "text/plain"})[0], 415)
        self.assertEqual(security.check("POST", "/api/start", {"Host": base["Host"]})[0], 415)

    def test_password(self):
        host = {"Host": "127.0.0.1"}
        self.assertEqual(security.check("GET", "/api/status", host, "pw")[0], 401)
        good = "Basic " + base64.b64encode(b"anyone:pw").decode()
        bad = "Basic " + base64.b64encode(b"anyone:nope").decode()
        self.assertIsNone(security.check("GET", "/api/status", {**host, "Authorization": good}, "pw"))
        self.assertEqual(security.check("GET", "/api/status", {**host, "Authorization": bad}, "pw")[0], 401)
        self.assertEqual(security.check("GET", "/api/status", {**host, "Authorization": "Basic !!!"}, "pw")[0], 401)
        self.assertIsNone(security.check("GET", "/health", {}, "pw"))  # the container health check carries no password


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "index.html").write_text("<html>report</html>", encoding="utf-8")
        cls.saved = (cs.REPORT_DIR, cs.PASSWORD, cs.TIMER_FILE)
        cs.REPORT_DIR, cs.TIMER_FILE = cls.tmp, cls.tmp / "timer.json"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cs.Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cs.REPORT_DIR, cs.PASSWORD, cs.TIMER_FILE = cls.saved

    def call(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_health_and_security_headers(self):
        status, headers, _ = self.call("GET", "/health")
        self.assertEqual(status, 200)
        status, headers, _ = self.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("Content-Security-Policy", self.call("GET", "/report/")[1])

    def test_foreign_host_is_refused_except_for_health(self):
        self.assertEqual(self.call("GET", "/api/status", headers={"Host": "evil.example"})[0], 421)
        self.assertEqual(self.call("GET", "/health", headers={"Host": "evil.example"})[0], 200)

    def test_cross_site_post_cannot_change_state(self):
        body = json.dumps({"seconds": 5})
        self.assertEqual(self.call("POST", "/api/timer", body, {"Content-Type": "text/plain", "Origin": "http://evil.example"})[0], 415)
        self.assertEqual(self.call("POST", "/api/timer", body, {**JSON, "Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.call("GET", "/api/timer")[2].decode().count('"counting"'), 0)

    def test_same_origin_post_works(self):
        origin = {"Origin": f"http://127.0.0.1:{self.port}"}
        status, _, data = self.call("POST", "/api/timer/cancel", b"", {**JSON, **origin})
        self.assertEqual(status, 409)  # it passed the guard; nothing is counting down
        self.assertIn("error", json.loads(data))

    def test_bad_bodies_are_answered_not_dropped(self):
        for body, expected in ((b"[1]", 400), (b"not json", 400), (b"", 413)):
            self.assertEqual(self.call("POST", "/api/start", body, JSON)[0], expected, body)

    def test_report_path_traversal_is_refused(self):
        for path in ("/report/../../etc/passwd", "/report/%2e%2e/%2e%2e/etc/passwd", "/legal/../VERSION"):
            self.assertEqual(self.call("GET", path)[0], 404, path)

    def test_password_protects_everything_but_health(self):
        cs.PASSWORD = "secret"
        try:
            self.assertEqual(self.call("GET", "/api/version")[0], 401)
            self.assertEqual(self.call("GET", "/health")[0], 200)
            auth = {"Authorization": "Basic " + base64.b64encode(b"u:secret").decode()}
            self.assertEqual(self.call("GET", "/api/version", headers=auth)[0], 200)
        finally:
            cs.PASSWORD = ""


class DockerExecTest(unittest.TestCase):
    def test_only_status_endpoints_of_plain_container_names(self):
        for container, url in (("ai-x; rm -rf /", "http://127.0.0.1:8080/health"), ("ai-x", "http://evil.example/health"),
                               ("ai-x", "http://127.0.0.1:8080/../etc"), ("--privileged", "http://127.0.0.1:1/slots"),
                               ("ai-x", "file:///etc/passwd")):
            with self.assertRaises(OSError, msg=(container, url)):
                cs.docker_exec_read(container, url)


if __name__ == "__main__":
    unittest.main()
