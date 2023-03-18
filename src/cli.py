import argparse
import json
import sys

import yaml
import pkg_resources

import dnspropagation

version = "0.0.2"

def main():
    dns_servers = []
    args_dict = {'json': False, 'simple': False, 'debug': False, 'dnslist': None, 'random': None, 'country': None,
                 'owner': None, 'expected': None, 'server': None, 'custom_list': None, 'show_default': False}

    parser = argparse.ArgumentParser()

    # Add optional arguments with no parameters
    parser.add_argument("--json",
                        action="store_true",
                        help="Print JSON output instead of a human-readable table.")
    parser.add_argument("--yaml",
                        action="store_true",
                        help="Print YAML output instead of a human-readable table.")
    parser.add_argument("--show-default",
                        action="store_true",
                        help="Show YAML-formattes list of default DNS servers.")
    parser.add_argument("--version",
                        action="store_true")


    parser.add_argument("--random",
                        type=int,
                        help="Selects N random DNS server to query")
    parser.add_argument("--country",
                        type=str,
                        action="append",
                        help="Use only DNS servers from given country. The argument can be used multiple times.")
    parser.add_argument("--owner",
                        type=str,
                        action="append",
                        help="Use only DNS servers from given owner. The argument can be used multiple times.")
    parser.add_argument("--expected",
                        type=str,
                        action="append",
                        help="Checks that DNS servers return expected values. The argument can be used multiple times.")
    parser.add_argument("--server",
                        type=str,
                        action="append",
                        help="IPv4 address of custom DNS server to query. Overrides default list. Can be used multiple times"
                             " to add multiple servers.")
    parser.add_argument("--custom_list",
                        type=str,
                        help="Path to custom YAML-formatted list of DNS servers to query.")
    parser.add_argument("--file",
                        type=str,
                        help="YAML formatted file")

    parser.add_argument("record_type",
                        metavar="TYPE",
                        type=str,
                        nargs="?",
                        help="Type of DNS record to check; e.g. TXT, A, CAA. Case insensitive.")
    parser.add_argument("domain",
                        metavar="DOMAIN",
                        type=str,
                        nargs="?",
                        help="Domain name to check; e.g. google.com")

    # Parse the arguments
    args = parser.parse_args()
    args_dict = vars(args)

    checker = dnspropagation.DNSpropagation()
    checker.set_args_dict(args_dict)



    if args_dict["version"]:
        print(version)
        exit(0)

    if len(sys.argv) <= 1:
        print("You have to specify record type and domain name. Run the program with the --help to show more information.")
        exit(1)

    if args_dict["custom_list"] is None and args_dict["server"] is None:
        dns_servers = checker.default_dns
        if args_dict["show_default"]:
            print(checker.default_dns)
            exit(0)

    if args_dict["file"] is None and (args_dict["record_type"] is None or args_dict["domain"] is None):
        print("You have to specify record type and domain name. Run the program with the --help to show more information.")
        exit(1)

    if args_dict['custom_list']:
        dns_servers = checker.parse_yaml(args_dict["custom_list"])
        checker.set_dns_servers(dns_servers)

    if args_dict["server"] is not None:
        for s in args_dict["server"]:
            tmp_server = {
                "ipv4": s,
                "owner": None,
                "country": None,
            }
            dns_servers.append(tmp_server)

    # filter DNS servers
    dns_servers = checker.filter_servers(dns_servers, args_dict["country"], args_dict["owner"])


    # run multiple checks at once
    if args_dict["file"] is not None:
        to_check = checker.parse_yaml(args_dict["file"])
        checker.multicheck(to_check, args_dict["country"], args_dict["owner"])
        exit(0)

    results = checker.check_entries(dns_servers, args_dict["record_type"], args_dict["domain"])

    if args_dict["json"]:
        print(json.dumps(checker.dns_answer_to_strings(results)))
        exit(0)
    elif args_dict["yaml"]:
        print(yaml.dump(checker.dns_answer_to_strings(results)))
        exit(0)


    checker.print_pretty_table(results, args_dict["expected"])



if __name__ == "__main__":
    main()
