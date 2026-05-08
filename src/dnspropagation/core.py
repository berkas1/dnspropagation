import copy
import importlib.resources
import ipaddress
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
import yaml
import dns.resolver
import json
from datetime import datetime
from pathlib import Path
from textwrap import fill
from prettytable import PrettyTable, ALL

_REMOTE_LIST_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
_REMOTE_LIST_TIMEOUT = 10  # seconds


class DNSpropagation:
    def __init__(self):
        self.args_dict = {'json': False, 'simple': False, 'debug': False, 'dnslist': None, 'random': None, 'country': None, 'owner': None, 'expected': None, 'server': None, 'custom_list': None, 'show_default': False}
        self.dns_servers = []
        self.default_dns = [{"ipv4": "8.8.8.8", "owner": "google", "tags": ["global", "unfiltered"]},
                       {"ipv4": "1.1.1.1", "owner": "cloudflare", "tags": ["global", "unfiltered"]},
                       {"ipv4": "1.1.1.3", "owner": "cloudflare", "tags": ["global", "adult-blocking"]},
                       {"ipv4": "193.17.47.1", "owner": "nic.cz", "tags": ["czechia", "unfiltered"]},
                       {"ipv4": "9.9.9.9", "owner": "quad9", "tags": ["switzerland", "unfiltered"]},
                       {"ipv4": "195.243.214.4", "owner": "Deutsche Telekom", "tags": ["germany", "unfiltered"]}]

    def set_args_dict(self, args_dict):
        self.args_dict = args_dict

    def set_dns_servers(self, dns_servers):
        self.dns_servers = dns_servers

    @staticmethod
    def _is_url(path: str) -> bool:
        return "://" in path

    def _fetch_remote_yaml(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            print(f"Error: unsupported URL scheme '{parsed.scheme}'. Only http and https are supported.")
            sys.exit(11)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dnspropagation"})
            with urllib.request.urlopen(req, timeout=_REMOTE_LIST_TIMEOUT) as resp:
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > _REMOTE_LIST_MAX_BYTES:
                    print("Error: remote server list exceeds the 1 MB size limit.")
                    sys.exit(12)
                data = resp.read(_REMOTE_LIST_MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            print(f"Error fetching remote server list: HTTP {exc.code} {exc.reason}")
            sys.exit(13)
        except urllib.error.URLError as exc:
            reason = exc.reason if isinstance(exc.reason, str) else str(exc.reason)
            print(f"Error fetching remote server list: {reason}")
            sys.exit(13)
        if len(data) > _REMOTE_LIST_MAX_BYTES:
            print("Error: remote server list exceeds the 1 MB size limit.")
            sys.exit(12)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            print("Error: remote server list is not valid UTF-8.")
            sys.exit(14)

    def _validate_server_list(self, servers) -> list:
        if not isinstance(servers, list):
            print("Error: server list must be a YAML sequence.")
            sys.exit(14)
        for i, entry in enumerate(servers):
            if not isinstance(entry, dict):
                print(f"Error: entry {i} is not a mapping.")
                sys.exit(14)
            if "ipv4" not in entry:
                print(f"Error: entry {i} is missing required 'ipv4' field.")
                sys.exit(14)
            try:
                ipaddress.ip_address(str(entry["ipv4"]))
            except ValueError:
                print(f"Error: entry {i} has an invalid IP address: {entry['ipv4']!r}")
                sys.exit(14)
        return servers

    def parse_yaml(self, file_path):
        if self._is_url(file_path):
            raw = self._fetch_remote_yaml(file_path)
            try:
                return yaml.safe_load(raw)
            except yaml.YAMLError as exc:
                print(f"Error parsing remote YAML: {exc}")
                sys.exit(14)
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print("specified file not found")
            sys.exit(10)
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML file: {exc}")
            sys.exit(14)

    def parse_server_list(self, path: str) -> list:
        """Load and validate a DNS server list from a local file or http(s):// URL."""
        data = self.parse_yaml(path)
        return self._validate_server_list(data)


    def dns_answer_to_strings(self, answer: [], show_ttl=False) -> []:
        output = []
        for a in answer:
            tmp = {'server': a["server"], 'answer': []}
            if show_ttl:
                tmp['ttl'] = a.get('ttl')
            for r in a["answer"]:
                if not isinstance(r, str):
                    tmp["answer"].append(r.to_text().strip('"'))
                else:
                    tmp["answer"].append(r.strip('"'))
            output.append(tmp)

        return output


    def filter_servers(self, data, tags=None, owner=None):
        filtered_data = []
        for item in data:
            tags_match = tags is None or all(t in (item.get("tags") or []) for t in tags)
            owner_match = owner is None or item["owner"] in owner
            if tags_match and owner_match:
                filtered_data.append(item)

        self.dns_servers = filtered_data
        return filtered_data


    # TODO
    def multicheck(self, data, country=None, owner=None):
        res = []
        for d in data:
            tmp = self.check_entries(self.dns_servers, d["type"], d["domain"])
            res.append(self.dns_answer_to_strings(tmp))

        print(json.dumps(res[0]))

    def random_servers(self, servers: [], n: int) -> []:
        return random.sample(servers, min(n, len(servers)))

    def sanitize_domain(self, domain: str) -> str:
        # Remove protocol (e.g. https://)
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        # Remove port number (e.g. :8080)
        domain = domain.split(":")[0]
        # Remove path / trailing slash
        domain = domain.split("/")[0]
        return domain

    def check_entries(self, servers: [], record_type, domain, timeout=None):
        results = []
        for server in servers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [server["ipv4"]]
                if timeout is not None:
                    resolver.lifetime = timeout
                answer = resolver.resolve(domain, record_type)
            except dns.resolver.NoAnswer:
                results.append({"server": server, "answer": [], "ttl": None})
            except dns.resolver.LifetimeTimeout:
                results.append({"server": server, "answer": ["timed out"], "ttl": None})
            except dns.resolver.NXDOMAIN:
                print("Domain not found.")
                exit(2)
            else:
                output = []
                for rdata in answer:
                    output.append(rdata)
                results.append({"server": server, "answer": output, "ttl": answer.rrset.ttl})

        return results

    def generate_html(self, results: [], record_type: str, domain: str, expected=None, show_ttl=False) -> str:
        rows = ""
        for result in results:
            answers = []
            for a in result["answer"]:
                text = a.to_text().strip('"') if not isinstance(a, str) else a.strip('"')
                if expected is not None and (text in expected or text[1:-1] in expected):
                    answers.append(f'<span class="ok">{text}</span>')
                elif expected is not None:
                    answers.append(f'<span class="fail">{text}</span>')
                elif text == "timed out":
                    answers.append(f'<span class="fail">{text}</span>')
                else:
                    answers.append(f'<span class="ok">{text}</span>')
            answer_html = "<br>".join(answers) if answers else '<span class="empty">—</span>'
            ttl_cell = f'<td>{result.get("ttl") or "—"}</td>' if show_ttl else ""
            tags_display = ", ".join(result["server"].get("tags") or []) or "—"
            rows += f"""
            <tr>
                <td>{result["server"]["ipv4"]}</td>
                <td>{tags_display}</td>
                {ttl_cell}
                <td>{answer_html}</td>
            </tr>"""

        ttl_header = "<th>TTL</th>" if show_ttl else ""
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            tmpl_text = (importlib.resources.files(__name__) / "templates" / "report.html").read_text(encoding="utf-8")
        except TypeError:
            tmpl_text = (Path(__file__).parent / "templates" / "report.html").read_text(encoding="utf-8")
        tmpl = string.Template(tmpl_text)
        return tmpl.substitute(
            record_type=record_type.upper(),
            domain=domain,
            generated_at=generated_at,
            rows=rows,
            ttl_header=ttl_header,
        )

    def compare_lists(self, list1, list2):
        l1 = copy.deepcopy(list1)
        l2 = copy.deepcopy(list2)

        return set(l1) == set(l2)


    def print_pretty_table(self, results: [], expected, show_ttl=False, no_color=False):
        x = PrettyTable()
        x.field_names = ["Server", "Tags", "TTL", "Answer"] if show_ttl else ["Server", "Tags", "Answer"]

        def colorize(code, text):
            if no_color:
                return text
            return f'\033[{code}m' + text + '\033[0m'

        for result in results:
            tmp_answer = ""
            answers = []
            for a in result["answer"]:
                if not isinstance(a, str):
                    tmp_string = a.to_text()
                else:
                    tmp_string = a

                if expected is not None and (tmp_string in expected or tmp_string[1:-1] in expected):
                    tmp_string = colorize(92, tmp_string)
                elif expected is not None and tmp_string not in expected:
                    tmp_string = colorize(91, tmp_string)
                elif result["answer"] == [] or result["answer"] is None:
                    tmp_string = colorize(93, "-")
                elif tmp_string == "timed out":
                    tmp_string = colorize(91, tmp_string)
                else:
                    tmp_string = colorize(92, tmp_string)
                answers.append(tmp_string)
            result_string = "\n".join(answers)
            tags_display = ", ".join(result["server"].get("tags") or [])
            if show_ttl:
                x.add_row([result["server"]["ipv4"], tags_display, result.get("ttl"), result_string])
            else:
                x.add_row([result["server"]["ipv4"], tags_display, result_string])


        x._max_width = {"Answer": 70}
        x.align["Answer"] = "l"
        x.hrules = ALL

        print(x)
