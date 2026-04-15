import copy
import random
import string
import sys
import yaml
import dns.resolver
import json
from datetime import datetime
from pathlib import Path
from textwrap import fill
from prettytable import PrettyTable, ALL


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

    def parse_yaml(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data
        except FileNotFoundError:
            print("specified file not found")
            sys.exit(10)


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

        template_path = Path(__file__).parent / "templates" / "report.html"
        tmpl = string.Template(template_path.read_text())
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


