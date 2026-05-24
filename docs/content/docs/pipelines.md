---
title: "Use in Pipelines"
weight: 20
---

# Use in Pipelines

dnspropagation is designed to integrate cleanly into shell scripts and CI/CD pipelines. Machine-readable output, predictable exit codes, and an assertion mode make it straightforward to gate a deployment or validate a DNS change.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing required arguments (TYPE or DOMAIN) |
| 2 | NXDOMAIN — domain does not exist |
| 3 | No servers matched the specified filters |
| 5 | `--expected` mismatch — at least one server returned an unexpected answer |
| 10 | Local file not found (`--custom_list` or `--file`) |
| 11 | Unsupported URL scheme (only `http`/`https` allowed) |
| 12 | Remote file exceeds the 1 MB size limit |
| 13 | Network error fetching remote list |
| 14 | YAML syntax error or non-UTF-8 response |
| 15 | HTTP error response from remote server (4xx / 5xx) |
| 16 | Server list schema validation failure |

---

## Asserting DNS Values

Use `--expected` to turn dnspropagation into a pass/fail check. If every queried server returns one of the expected values the exit code is 0; if any server returns something different the exit code is 5.

```bash
dnspropagation --expected 93.184.216.34 A example.com
echo "Exit code: $?"
```

Multiple expected values are accepted (useful for round-robin or dual-stack records):

```bash
dnspropagation \
  --expected 8.8.8.8 \
  --expected 8.8.4.4 \
  A dns.google
```

Timeouts are not counted as mismatches — they are skipped during the expected-value check.

---

## Shell Script Example

Wait until a newly published record propagates to all default resolvers before continuing a deployment:

```bash
#!/usr/bin/env bash
set -euo pipefail

DOMAIN="example.com"
EXPECTED_IP="203.0.113.42"
MAX_ATTEMPTS=20
SLEEP_SECONDS=30

for i in $(seq 1 "$MAX_ATTEMPTS"); do
  echo "Attempt $i/$MAX_ATTEMPTS..."
  if dnspropagation --no-color --expected "$EXPECTED_IP" A "$DOMAIN"; then
    echo "Propagation confirmed."
    exit 0
  fi
  sleep "$SLEEP_SECONDS"
done

echo "Propagation did not complete within the timeout." >&2
exit 1
```

---

## GitHub Actions Example

Add a propagation check as a step in a deployment workflow:

```yaml
- name: Wait for DNS propagation
  run: |
    pip install dnspropagation
    dnspropagation \
      --no-color \
      --tags global,unfiltered \
      --expected "${{ vars.EXPECTED_IP }}" \
      A "${{ vars.DOMAIN }}"
```

Exit code 5 causes the step to fail, blocking downstream deployment steps.

---

## Parsing JSON Output

Use `--json` to get structured output for further processing:

```bash
# Extract all answers with jq
dnspropagation --json A example.com | jq '.[].answer[]'

# Check whether any server returned a specific value
dnspropagation --json A example.com \
  | jq --arg ip "93.184.216.34" \
       'any(.[].answer[]; . == $ip)'
```

---

## Batch Checks

Run multiple record checks in a single invocation with `--file`. Output is always JSON, making it suitable for further processing or archival.

```yaml
# checks.yaml
- type: A
  domain: example.com
- type: MX
  domain: example.com
- type: TXT
  domain: example.com
```

```bash
dnspropagation --file checks.yaml | jq .
```

---

## Tips

- Use `--no-color` whenever output is captured or logged — it removes ANSI escape codes that can corrupt log files.
- Use `--timeout` to set an aggressive per-query deadline in time-sensitive pipelines.
- Use `--tags` or `--owner` to limit checks to specific regions or providers during a staged rollout.
- Use `--random N` for periodic sampling against a large custom resolver list without querying every server on every run.
