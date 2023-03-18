# dnspropagation

Simple CLI utility to check propagation of DNS records using multiple DNS servers.

## Installation
```
pip install dnspropagation
```

## Usage
In the most simple form you can just specify type of record and domain name:
```
dnspropagation a google.com
```

It will check entries for a given type and domain name using five default public nameservers. It returns a human-readable colorful table. You can use `--json` or `--yaml` parameters to make it machine-readable.

![Table 1](extras/table1.png)

### Custom DNS servers
You can either supply custom DNS server to query using the `--server` parameter, which can be used multiple times:
```shell
dnspropagation --server 1.1.1.1 --server 8.8.8.8 a google.com
```

OR you can add a yaml-formatted list of servers. This has to follow given format (as can be seen in [this](custom-list.yaml) file) and be supplied to the utility using the `--custom_list` parameter.


### Expected results
You can expect a value to be returned by DNS servers. If this value is returned, its color will be green. Otherwise the value will be shown red.
![expect1](extras/expect1.png)

### Filtering DNS servers
When using the default DNS servers or a custom list, you can limit which servers you want to query using parameters `--country` and `--owner`.
Both can be used multiple times. When used, the AND operation is used.

![owner](extras/owner1.png)

