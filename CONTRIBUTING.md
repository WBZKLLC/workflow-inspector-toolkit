# Contributing

Keep this toolkit small, local, and explainable. A useful change should improve file validation, descriptive analysis, clear limitations, documentation, or reproducible examples.

Before opening a pull request, run:

```bash
python -m unittest discover -s tests -v
python scripts/check_release.py
```

Use fictional reference codes and invented timestamps only. Do not include customer data, actual operational exports, access tokens, payment details, deployment configuration, or internal documents. Verify the diff and staged file list before submitting. A secrets-pattern check is not a complete security audit.

Do not add fabricated testimonials, vendor endorsements, adoption counts, savings claims, or a passing-CI claim without supporting evidence. Do not describe a manual CSV mapping as a native connection.

Tests should preserve the distinction between a measured zero and a missing value. Pair matching must remain explicit; ambiguous histories should not be silently repaired. Changes to input or output semantics need documentation and a versioned contract decision.

For security reports, follow [SECURITY.md](SECURITY.md). For ordinary bugs, include the command, expected result, actual result, and a synthetic reproduction. Never attach your real customer export.
