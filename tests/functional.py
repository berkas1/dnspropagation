import json
import os
import subprocess
import tempfile

import yaml


def run(*args):
    return subprocess.run(
        ['python', 'src/cli.py', *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
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
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data == []


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
    result = run('--server', '8.8.8.8', '--expected', '8.8.8.8', 'A', 'dns.google')
    assert result.returncode == 0


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
