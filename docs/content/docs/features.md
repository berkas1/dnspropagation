---
title: "Features"
weight: 10
---

# Features

## Basic Usage

```
dnspropagation [OPTIONS] TYPE DOMAIN
```

`TYPE` is any DNS record type (A, AAAA, TXT, MX, CNAME, CAA, …). It is case-insensitive. `DOMAIN` is stripped of any protocol, port, or path — `https://example.com:443/path` is treated as `example.com`.

---

## Output Formats

### Table (default)

Prints a colour-coded PrettyTable to stdout. Answers matching `--expected` are green, mismatches are red, empty answers are yellow, and timeouts are red.

### `--json`

Outputs a JSON array. Each element represents one server:

```json
[
  {
    "server": {
      "ipv4": "8.8.8.8",
      "owner": "google",
      "tags": ["global", "unfiltered"]
    },
    "answer": ["142.250.185.46"]
  }
]
```

### `--yaml`

Same structure as JSON, printed as YAML.

### `--html`

Writes a self-contained HTML page (embedded CSS, no external dependencies) to stdout. Pipe it to a file:

```bash
dnspropagation --html A example.com > report.html
```

### `--no-color`

Disables ANSI escape codes in table output. Useful when piping to a file or a CI log viewer that does not interpret colour codes.

### `--ttl`

Adds a TTL column (or field) to the output showing the time-to-live value returned by each server.

---

## Server Selection

### `--server IP`

Add a specific resolver by IPv4 address. Can be repeated. When at least one `--server` flag is given, the default server list is not used.

```bash
dnspropagation --server 8.8.8.8 --server 1.1.1.1 A example.com
```

### `--custom_list PATH_OR_URL`

Load servers from a YAML file on disk or over HTTP/HTTPS. Remote files are fetched with a 10-second timeout and must be under 1 MB.

Required YAML schema:

```yaml
- ipv4: "1.1.1.1"        # required — must be a valid IPv4 address
  owner: "cloudflare"    # optional
  tags:                  # optional
    - global
    - unfiltered
```

```bash
dnspropagation --custom_list ./my-servers.yaml A example.com
dnspropagation --custom_list https://example.com/resolvers.yaml A example.com
```

### `--random N`

Randomly sample N servers from the active list before querying. Useful for ad-hoc spot-checks against a large custom list.

```bash
dnspropagation --random 3 A example.com
```

---

## Filtering

### `--tags TAG[,TAG...]`

Keep only servers that have **all** specified tags (AND logic). Can be repeated; comma-separated values are flattened.

```bash
# Only global unfiltered resolvers
dnspropagation --tags global,unfiltered A example.com

# Same result, two flags
dnspropagation --tags global --tags unfiltered A example.com
```

### `--owner NAME`

Keep only servers whose owner matches NAME. Can be repeated; matching is OR logic across values.

```bash
# Only Google and Cloudflare
dnspropagation --owner google --owner cloudflare A example.com
```

Tags and owner filters can be combined — only servers satisfying both conditions are queried.

---

## Query Options

### `--timeout SECONDS`

Per-query timeout as a float. If a server does not respond within this time its answer is recorded as `["timed out"]`.

```bash
dnspropagation --timeout 1.5 A example.com
```

### `--expected VALUE`

Assert that every server returns VALUE. Can be repeated to allow multiple valid answers. Servers whose answer does not match any expected value cause the tool to exit with code 5. Timeouts are excluded from this check.

```bash
dnspropagation --server 8.8.8.8 --expected 93.184.216.34 A example.com
```

---

## Batch Mode

### `--file PATH`

Run multiple record/domain queries defined in a YAML file. Output is always JSON.

```yaml
- type: A
  domain: example.com
- type: TXT
  domain: example.com
- type: MX
  domain: example.com
```

```bash
dnspropagation --file checks.yaml
```

---

## Utility

### `--show-default`

Print the built-in server list to stdout. Add `--yaml` to get YAML output.

```bash
dnspropagation --show-default
dnspropagation --show-default --yaml
```

### `--version`

Print the installed version and exit.
