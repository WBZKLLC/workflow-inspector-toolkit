# Security and privacy

## Supported scope

This policy covers Workflow Inspector Toolkit 0.1.x. This is local software, not an internet-facing service. No authentication, hosted API, payment processing, customer database, or live provider connection is included.

## Reporting a possible vulnerability

Use GitHub's private vulnerability reporting option in this repository when that option is enabled. Otherwise, use a current private contact route listed on [Workflow Inspector's website](https://workflow-inspector.com) to request a secure reporting channel. Do not post credentials, real customer records, or exploit details that expose confidential information in a public issue. This repository does not claim an enabled private-reporting setting or a staffed response-time guarantee until those are actually configured.

A helpful report contains the affected toolkit version, expected and actual behavior, and a minimal reproduction with fictional records. Remove all business-sensitive data before sharing.

## Data precautions

Run on trusted local storage. Keep real inputs in `local-data/` and generated outputs in `local-reports/`; both are gitignored. Ignoring a directory is not a substitute for reviewing every staged file, and `git add -f` can override ignore rules.

Use reference codes rather than personal identifiers. Restricted syntax reduces accidental email, URL, and spreadsheet-formula exposure but does not prove anonymization. Names or sensitive values can still be encoded in allowed references. A validation pass is not a privacy review.

Do not commit real reports or input hashes from sensitive datasets. Hashes allow comparison and may reveal dataset identity. HTML reports omit case references but still contain potentially confidential operational statistics.

## Technical controls and limits

Inputs are bounded and parsed as data, not executed. Unknown fields, invalid timestamps, duplicate event references, and ambiguous JSON keys are rejected. No runtime network calls or tracking are included. HTML text is escaped, remote assets and scripts are absent, and a restrictive content-security policy is embedded.

These controls do not verify source authenticity, operating-system security, file permissions, secure deletion, or the absence of all vulnerabilities. Use synthetic inputs in bug reports and CI.
