---
title: "dnspropagation"
---

# dnspropagation

**dnspropagation** is a command-line tool that checks DNS record "propagation" across multiple resolvers simultaneously. Run a single command and see what different nameservers around the world return for any record type.

## Installation

```bash
pipx install dnspropagation
```

Or run directly with Docker — no installation required:

```bash
docker run berkas1/dnspropagation A google.com
```

## Quick Start

```bash
# Check A records for google.com across all default servers
dnspropagation A google.com
docker run berkas1/dnspropagation A google.com

# Check TXT records and show TTL values
dnspropagation --ttl TXT example.com

# Output as JSON for scripting
dnspropagation --json A example.com
```

By default, the tool queries six public resolvers (Google, Cloudflare, Quad9, NIC.CZ, Deutsche Telekom) and prints a colour-coded table showing each server's answer.

## Default Servers

| IP | Owner | Tags |
|----|-------|------|
| 8.8.8.8 | Google | global, unfiltered |
| 1.1.1.1 | Cloudflare | global, unfiltered |
| 1.1.1.3 | Cloudflare | global, adult-blocking |
| 193.17.47.1 | NIC.CZ | czechia, unfiltered |
| 9.9.9.9 | Quad9 | switzerland, unfiltered |
| 195.243.214.4 | Deutsche Telekom | germany, unfiltered |

## Output Formats

dnspropagation supports four output formats:

- **Table** (default) — colour-coded terminal table
- **JSON** (`--json`) — machine-readable JSON array
- **YAML** (`--yaml`) — machine-readable YAML
- **HTML** (`--html`) — self-contained HTML page written to stdout

See [Features]({{< relref "/docs/features" >}}) for a full description of all options and [Use in Pipelines]({{< relref "/docs/pipelines" >}}) for CI/CD integration patterns.
