import copy
import sys
import yaml
import dns.resolver
import json
from textwrap import fill
from prettytable import PrettyTable, ALL


class DNSpropagation:
    def __init__(self):
        self.args_dict = {'json': False, 'simple': False, 'debug': False, 'dnslist': None, 'random': None, 'country': None, 'owner': None, 'expected': None, 'server': None, 'custom_list': None, 'show_default': False}
        self.dns_servers = []
        self.default_dns = [{"ipv4": "8.8.8.8", "owner": "google", "country": "global"},
                       {"ipv4": "1.1.1.1", "owner": "cloudflare", "country": "global"},
                       {"ipv4": "193.17.47.1", "owner": "nic.cz", "country": "Czechia"},
                       {"ipv4": "9.9.9.9", "owner": "quad9", "country": "Switzerland"},
                       {"ipv4": "195.243.214.4", "owner": "Deutsche Telekom", "country": "Germany"}]

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


    def dns_answer_to_strings(self, answer: []) -> []:
        output = []
        for a in answer:
            tmp = {'server': a["server"], 'answer': []}
            for r in a["answer"]:
                if not isinstance(r, str):
                    tmp["answer"].append(r.to_text().strip('"'))
                else:
                    tmp["answer"].append(r.strip('"'))
            output.append(tmp)

        return output


    def filter_servers(self, data, country=None, owner=None):
        filtered_data = []
        for item in data:
            if (country is None or item["country"] in country) and (owner is None or item["owner"] in owner):
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

    def check_entries(self, servers: [], record_type, domain):
        results = []
        for server in servers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [server["ipv4"]]
                answer = resolver.resolve(domain, record_type)
            except dns.resolver.NoAnswer:
                results.append({"server": server, "answer": []})
            except dns.resolver.LifetimeTimeout:
                results.append({"server": server, "answer": ["timed out"]})
            except dns.resolver.NXDOMAIN:
                print("Domain not found.")
                exit(2)
            else:
                output = []
                for rdata in answer:
                    output.append(rdata)
                results.append({"server": server, "answer": output})

        return results

    def compare_lists(self, list1, list2):
        l1 = copy.deepcopy(list1)
        l2 = copy.deepcopy(list2)

        return set(l1) == set(l2)


    def print_pretty_table(self, results: [], expected):
        x = PrettyTable()
        x.field_names = ["Server", "Location", "Answer"]

        for result in results:
            tmp_answer = ""
            answers = []
            for a in result["answer"]:
                if not isinstance(a, str):
                    tmp_string = a.to_text()
                else:
                    tmp_string = a

                if expected is not None and (tmp_string in expected or tmp_string[1:-1] in expected):
                    tmp_string = '\033[92m' + tmp_string + '\033[0m'
                elif expected is not None and tmp_string not in expected:
                    tmp_string = '\033[91m' + tmp_string + '\033[0m'
                elif result["answer"] == [] or result["answer"] is None:
                    tmp_string = '\033[93m' + "-" + '\033[0m'
                elif tmp_string == "timed out":
                    tmp_string = '\033[91m' + "timed out" + '\033[0m'
                else:
                    tmp_string = '\033[92m' + tmp_string + '\033[0m'
                answers.append(tmp_string)
            result_string = "\n".join(answers)
            x.add_row([result["server"]["ipv4"], result["server"]["country"], result_string])


        x._max_width = {"Answer": 70}
        x.align["Answer"] = "l"
        x.hrules = ALL

        print(x)


