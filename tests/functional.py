import json
import subprocess


def test_no_parameter():
    result = subprocess.run(['python', 'src/cli.py'], stdout=subprocess.PIPE)

    assert result.returncode == 1


def test_one_parameter():
    result = subprocess.run(['python', 'src/cli.py', 'txt'], stdout=subprocess.PIPE)

    assert str(result.stdout).find("You have to specify record type and domain name") >= 0
    assert result.returncode == 1


def test_ok_google_dns():
    result = subprocess.run(
        ['python', 'src/cli.py', '--server', '8.8.8.8', 'A', 'dns.google'],
        stdout=subprocess.PIPE
    )

    assert result.returncode == 0
    output = result.stdout.decode()
    assert "8.8.8.8" in output
    assert "8.8.4.4" in output


def test_ok_google_dns_yaml():
    result = subprocess.run(
        ['python', 'src/cli.py', '--yaml', '--server', '8.8.8.8', 'A', 'dns.google'],
        stdout=subprocess.PIPE
    )

    assert result.returncode == 0
    output = result.stdout.decode()
    assert "8.8.8.8" in output
    assert "8.8.4.4" in output


def test_ok_google_dns_json():
    result = subprocess.run(
        ['python', 'src/cli.py', '--json', '--server', '8.8.8.8', 'A', 'dns.google'],
        stdout=subprocess.PIPE
    )

    assert result.returncode == 0
    data = json.loads(result.stdout.decode())
    answers = data[0]["answer"]
    assert "8.8.8.8" in answers
    assert "8.8.4.4" in answers


def test_domain_not_found():
    result = subprocess.run(
        ['python', 'src/cli.py', 'A', 'example.not.existing'],
        stdout=subprocess.PIPE
    )

    assert result.returncode == 2
    assert "Domain not found" in result.stdout.decode()


def test_ok_google_dns_json_ttl():
    result = subprocess.run(
        ['python', 'src/cli.py', '--json', '--ttl', '--server', '8.8.8.8', 'A', 'dns.google'],
        stdout=subprocess.PIPE
    )

    assert result.returncode == 0
    data = json.loads(result.stdout.decode())
    assert "ttl" in data[0]
    assert isinstance(data[0]["ttl"], int)
    assert data[0]["ttl"] > 0
