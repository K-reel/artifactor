# Security Policy

## Supported Versions

We support the latest release and `main` branch with security updates.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| v0.1.x  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Artifactor, please report it by:

1. **Opening a GitHub issue** at https://github.com/K-reel/artifactor/issues
   - Mark the issue with the `security` label
   - Provide a clear description of the vulnerability

2. **Include the following information:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

**Response time:** We aim to respond to security reports within 48 hours.

## Security Considerations

Artifactor is designed with security in mind:

- **No credentials in fixtures**: Test data uses synthetic content only
- **Offline-first testing**: CI runs without network access by default
- **Dependency pinning**: Gemfile.lock and pip dependencies tracked
- **Input validation**: URLs and file paths validated before processing
- **Safe HTML handling**: BeautifulSoup parses HTML defensively

## Out of Scope

The following are not considered security vulnerabilities:

- Issues in dependencies (report to the upstream project)
- Denial of service via extremely large input files (use `--limit` flag)
- Social engineering attacks targeting repository contributors
