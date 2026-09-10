# Security policy

Report vulnerabilities privately to adammor17@gmail.com — do not open public
issues for security findings. Expected response: within 5 business days.

## Hardening baseline
- Secrets never in repo. `.env` is gitignored; use `.env.example` as a template.
- pre-commit + gitleaks scans every commit; commits are SSH-signed.
- Dependencies: run `pip-audit` (Python) / `pnpm audit` (Node) / `trivy fs .` regularly.
