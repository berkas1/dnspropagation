import json
import os
import socket
import subprocess
import tempfile

import yaml

from conftest import serve_yaml


def run(*args):
    env = {**os.environ, 'PYTHONPATH': 'src'}
    return subprocess.run(
        ['python', '-m', 'dnspropagation.cli', *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )


# --- argument validation ---

def test_no_parameter():
    result = run()
    assert result.returncode == 1


def test_one_parameter():
    result = run('txt')
    assert b"You have to specify record type and domain name" in result.stdout
    assert result.returncode == 1


def test_version():
    result = run('--version')
    assert result.returncode == 0
    assert result.stdout.strip() != b""


def test_show_default():
    result = run('--show-default')
    assert result.returncode == 0
    assert b"8.8.8.8" in result.stdout


def test_show_default_yaml():
    result = run('--show-default', '--yaml')
    assert result.returncode == 0
    data = yaml.safe_load(result.stdout)
    assert isinstance(data, list)
    assert any(s["ipv4"] == "8.8.8.8" for s in data)


# --- domain sanitization ---

def test_sanitize_protocol():
    result = run('--json', '--server', '8.8.8.8', 'A', 'https://dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


def test_sanitize_trailing_slash():
    result = run('--json', '--server', '8.8.8.8', 'A', 'dns.google/')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


def test_sanitize_port():
    result = run('--json', '--server', '8.8.8.8', 'A', 'dns.google:8080')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


def test_sanitize_protocol_port_path():
    result = run('--json', '--server', '8.8.8.8', 'A', 'https://dns.google:443/some/path')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


# --- A record: dns.google ---

def test_ok_google_dns():
    result = run('--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    output = result.stdout.decode()
    assert "8.8.8.8" in output
    assert "8.8.4.4" in output


def test_ok_google_dns_yaml():
    result = run('--yaml', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    output = result.stdout.decode()
    assert "8.8.8.8" in output
    assert "8.8.4.4" in output


def test_ok_google_dns_json():
    result = run('--json', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    answers = data[0]["answer"]
    assert "8.8.8.8" in answers
    assert "8.8.4.4" in answers


# --- TXT record ---

def test_txt_record():
    result = run('--json', '--server', '8.8.8.8', 'TXT', 'google.com')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


# --- TTL ---

def test_ok_google_dns_json_ttl():
    result = run('--json', '--ttl', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ttl" in data[0]
    assert isinstance(data[0]["ttl"], int)
    assert data[0]["ttl"] > 0


def test_ttl_absent_without_flag():
    result = run('--json', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "ttl" not in data[0]


def test_ttl_yaml_output():
    result = run('--yaml', '--ttl', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = yaml.safe_load(result.stdout)
    assert "ttl" in data[0]
    assert isinstance(data[0]["ttl"], int)


# --- filtering ---

def test_filter_owner():
    result = run('--json', '--owner', 'google', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["server"]["owner"] == "google"


def test_filter_owner_multiple():
    result = run('--json', '--owner', 'google', '--owner', 'cloudflare', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 3
    owners = {d["server"]["owner"] for d in data}
    assert owners == {"google", "cloudflare"}


def test_filter_tags():
    result = run('--json', '--tags', 'czechia', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert "czechia" in data[0]["server"]["tags"]


def test_filter_tags_multiple_must_all_match():
    # "global,unfiltered" — server must have both tags; adult-blocking server has global but not unfiltered
    result = run('--json', '--tags', 'global,unfiltered', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert all("global" in s["server"]["tags"] and "unfiltered" in s["server"]["tags"] for s in data)
    assert not any("adult-blocking" in s["server"]["tags"] for s in data)


def test_filter_nonexistent_owner_returns_empty():
    result = run('--json', '--owner', 'nonexistent_owner_xyz', 'A', 'dns.google')
    assert result.returncode == 3


# --- multiple servers ---

def test_multiple_servers():
    result = run('--json', '--server', '8.8.8.8', '--server', '1.1.1.1', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 2


def test_json_structure():
    result = run('--json', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    entry = data[0]
    assert "server" in entry
    assert "answer" in entry
    assert "ipv4" in entry["server"]
    assert "owner" in entry["server"]
    assert "tags" in entry["server"]


# --- custom list ---

def test_custom_list():
    result = run('--json', '--custom_list', 'custom-list.yaml', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 5


def test_custom_list_not_found():
    result = run('--json', '--custom_list', 'nonexistent.yaml', 'A', 'dns.google')
    assert result.returncode == 10


def test_custom_list_tmp():
    servers = [{"ipv4": "8.8.8.8", "owner": "google", "tags": ["global"]}]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(servers, f)
        tmp_path = f.name
    try:
        result = run('--json', '--custom_list', tmp_path, 'A', 'dns.google')
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["server"]["ipv4"] == "8.8.8.8"
    finally:
        os.unlink(tmp_path)


# --- expected values ---

def test_expected_match():
    # dns.google returns 8.8.8.8 and 8.8.4.4 — both must be listed as expected for exit 0
    result = run('--server', '8.8.8.8', '--expected', '8.8.8.8', '--expected', '8.8.4.4', 'A', 'dns.google')
    assert result.returncode == 0


def test_expected_no_match():
    result = run('--server', '8.8.8.8', '--expected', '1.2.3.4', 'A', 'dns.google')
    assert result.returncode == 5


def test_expected_no_match_json_still_outputs():
    result = run('--json', '--server', '8.8.8.8', '--expected', '1.2.3.4', 'A', 'dns.google')
    assert result.returncode == 5
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


# --- no-color ---

def test_no_color_suppresses_ansi():
    result = run('--no-color', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    assert b'\033[' not in result.stdout


def test_default_output_contains_ansi():
    # --expected always colorizes, so ANSI codes must be present without --no-color
    result = run('--server', '8.8.8.8', '--expected', '8.8.8.8', '--expected', '8.8.4.4', 'A', 'dns.google')
    assert result.returncode == 0
    assert b'\033[' in result.stdout


def test_no_color_with_expected_match():
    result = run('--no-color', '--server', '8.8.8.8', '--expected', '8.8.8.8', '--expected', '8.8.4.4', 'A', 'dns.google')
    assert result.returncode == 0
    assert b'\033[' not in result.stdout


def test_no_color_with_expected_mismatch():
    result = run('--no-color', '--server', '8.8.8.8', '--expected', '1.2.3.4', 'A', 'dns.google')
    assert result.returncode == 5
    assert b'\033[' not in result.stdout


# --- random ---

def test_random_selects_n_servers():
    result = run('--json', '--random', '2', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 2


def test_random_one_server():
    result = run('--json', '--random', '1', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1


def test_random_exceeds_pool_returns_all():
    # there are 6 default servers; requesting more should return all 6
    result = run('--json', '--random', '100', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 6


def test_random_respects_tags_filter():
    # only 1 server has both "czechia" and "unfiltered", random 2 should still return 1
    result = run('--json', '--random', '2', '--tags', 'czechia,unfiltered', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert "czechia" in data[0]["server"]["tags"]


# --- timeout ---

def test_timeout_valid():
    result = run('--json', '--timeout', '5', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


def test_timeout_float():
    result = run('--json', '--timeout', '2.5', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data[0]["answer"]) > 0


def test_timeout_triggers():
    # 0.001s timeout against a real server should always time out
    result = run('--json', '--timeout', '0.001', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data[0]["answer"] == ["timed out"]


# --- NXDOMAIN ---

def test_domain_not_found():
    result = run('A', 'example.not.existing')
    assert result.returncode == 2
    assert b"Domain not found" in result.stdout


# --- remote HTTP custom list ---

def test_custom_list_http():
    servers = [{"ipv4": "8.8.8.8", "owner": "google", "tags": ["global"]}]
    with serve_yaml(yaml.dump(servers).encode()) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["server"]["ipv4"] == "8.8.8.8"


def test_custom_list_http_unsupported_scheme():
    result = run('--json', '--custom_list', 'ftp://example.com/list.yaml', 'A', 'dns.google')
    assert result.returncode == 11


def test_custom_list_http_unreachable():
    # Bind then immediately close to get a guaranteed free port (connection refused)
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    result = run('--json', '--custom_list', f'http://127.0.0.1:{port}/list.yaml', 'A', 'dns.google')
    assert result.returncode == 13


def test_custom_list_http_error_response():
    with serve_yaml(b"", status=404) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 15


def test_custom_list_http_missing_ipv4_field():
    bad = [{"owner": "nobody", "tags": []}]
    with serve_yaml(yaml.dump(bad).encode()) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 16


def test_custom_list_http_invalid_ip():
    bad = [{"ipv4": "not-an-ip", "owner": "nobody", "tags": []}]
    with serve_yaml(yaml.dump(bad).encode()) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 16


def test_custom_list_local_invalid_ip():
    bad = [{"ipv4": "999.999.999.999", "owner": "nobody", "tags": []}]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(bad, f)
        tmp_path = f.name
    try:
        result = run('--json', '--custom_list', tmp_path, 'A', 'dns.google')
        assert result.returncode == 16
    finally:
        os.unlink(tmp_path)


def test_custom_list_local_malformed_yaml():
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.yaml', delete=False) as f:
        f.write(b"key: [unclosed bracket\n")
        tmp_path = f.name
    try:
        result = run('--json', '--custom_list', tmp_path, 'A', 'dns.google')
        assert result.returncode == 14
    finally:
        os.unlink(tmp_path)


def test_custom_list_http_malformed_yaml():
    with serve_yaml(b"key: [unclosed bracket\n") as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 14


def test_empty_server_list_after_filter():
    result = run('--json', '--tags', 'nonexistent_tag_xyz', 'A', 'dns.google')
    assert result.returncode == 3


# --- HTML output ---

def test_html_output_structure():
    result = run('--html', '--server', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0
    assert b"<html" in result.stdout.lower()
    assert b"8.8.8.8" in result.stdout
    assert b'class="ok"' in result.stdout


def test_html_expected_mismatch_marked_fail():
    result = run('--html', '--server', '8.8.8.8', '--expected', '1.2.3.4', 'A', 'dns.google')
    assert result.returncode == 5
    assert b'class="fail"' in result.stdout


# These two tests call the core class directly (not via the CLI) because
# the markup has to come from a DNS answer, which cannot be injected end-to-end.

def test_html_escapes_untrusted_values():
    from dnspropagation.core import DNSpropagation
    results = [{
        "server": {"ipv4": "1.1.1.1", "tags": ["<b>tag</b>"]},
        "answer": ['"<script>alert(1)</script>"'],
        "ttl": 60,
    }]
    page = DNSpropagation().generate_html(results, "txt", "a<img src=x>.com", show_ttl=True)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<b>tag</b>" not in page
    assert "&lt;b&gt;tag&lt;/b&gt;" in page
    assert "<img src=x>" not in page
    assert "a&lt;img src=x&gt;.com" in page


def test_html_expected_matches_raw_text_not_escaped():
    from dnspropagation.core import DNSpropagation
    results = [{"server": {"ipv4": "1.1.1.1", "tags": []}, "answer": ["a<b"], "ttl": 1}]
    page = DNSpropagation().generate_html(results, "txt", "example.com", expected=["a<b"])
    assert '<span class="ok">a&lt;b</span>' in page


# --- record text conversion ---

class _FakeRdata:
    """Minimal stand-in for a dnspython rdata object."""
    def __init__(self, text):
        self._text = text

    def to_text(self):
        return self._text


def test_record_text_handles_rdata_and_strings():
    from dnspropagation.core import DNSpropagation
    conv = DNSpropagation._record_text
    assert conv("plain") == "plain"
    assert conv(_FakeRdata('"quoted"')) == '"quoted"'
    assert conv('"quoted"', strip_quotes=True) == "quoted"
    assert conv(_FakeRdata('"quoted"'), strip_quotes=True) == "quoted"


def test_dns_answer_to_strings_strips_quotes():
    from dnspropagation.core import DNSpropagation
    answer = [{"server": {"ipv4": "1.1.1.1"}, "answer": [_FakeRdata('"v=spf1 -all"'), '"x"'], "ttl": 5}]
    out = DNSpropagation().dns_answer_to_strings(answer, show_ttl=True)
    assert out == [{"server": {"ipv4": "1.1.1.1"}, "answer": ["v=spf1 -all", "x"], "ttl": 5}]


# --- schema validation edge cases ---

def test_custom_list_not_a_list():
    with serve_yaml(yaml.dump({"ipv4": "8.8.8.8"}).encode()) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 16
    assert b"must be a YAML sequence" in result.stdout


def test_custom_list_entry_not_a_mapping():
    with serve_yaml(yaml.dump(["8.8.8.8"]).encode()) as url:
        result = run('--json', '--custom_list', url, 'A', 'dns.google')
    assert result.returncode == 16
    assert b"is not a mapping" in result.stdout


# --- terminal escape injection ---

def test_strip_control_chars():
    from dnspropagation.core import DNSpropagation
    strip = DNSpropagation._strip_control_chars
    assert strip("plain, tags-1") == "plain, tags-1"
    assert strip("\x1b]0;PWNED\x07\x1b[2J evil\n") == "]0;PWNED[2J evil"


def test_pretty_table_strips_escapes_from_tags(capsys):
    from dnspropagation.core import DNSpropagation
    results = [{"server": {"ipv4": "1.1.1.1", "tags": ["\x1b]0;PWNED\x07\x1b[2J evil"]}, "answer": ["1.2.3.4"], "ttl": 5}]
    DNSpropagation().print_pretty_table(results, None, no_color=True)
    out = capsys.readouterr().out
    assert "\x1b" not in out and "\x07" not in out
    assert "evil" in out


def test_custom_list_escape_in_tags_not_printed():
    data = [{"ipv4": "127.0.0.1", "tags": ["\x1b[2J evil"]}]
    with serve_yaml(yaml.dump(data).encode()) as url:
        result = run('--no-color', '--timeout', '1', '--custom_list', url, 'A', 'dns.google')
    assert b"\x1b" not in result.stdout
    assert b"evil" in result.stdout


# --- empty answer ---

def test_no_answer_returns_empty_list():
    # www.google.com has no TXT records, so the server answers with NoAnswer
    result = run('--json', '--ttl', '--server', '8.8.8.8', 'TXT', 'www.google.com')
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data[0]["answer"] == []
    assert data[0]["ttl"] is None
