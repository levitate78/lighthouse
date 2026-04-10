# Security Policy

## Supported Versions

This project is developed in spare time and provided on a best-effort basis. Security updates are not guaranteed for all versions.

| Version | Supported |
| ------- | --------- |
| Latest  | ✅ Yes     |
| Older   | ❌ No      |

Users are strongly encouraged to run the latest version at all times.

---

## Reporting a Vulnerability

If you discover a security vulnerability, do **not** open a public issue.

Instead, report it via an advisory: [[https://github.com/levitate78/lighthouse/security/advisories/new]]

Please include:

* A clear description of the vulnerability
* Steps to reproduce the issue
* Any relevant logs, screenshots, or proof-of-concept code
* Your assessment of potential impact (if known)

---

## Response Expectations

As this project is maintained in spare time:

* Initial response may take **up to 30 days**
* Fix timelines will vary depending on complexity and availability
* Critical vulnerabilities will be prioritised where possible

There is no formal SLA.

---

## Disclosure Policy

* Vulnerabilities should not be publicly disclosed until a fix is available or agreed upon
* Coordinated disclosure is appreciated
* Credit will be given to reporters unless anonymity is requested

---

## Scope

This policy applies to:

* The core web application
* Public APIs exposed by the application
* Deployment configurations provided in the repository

Out of scope:

* Third-party dependencies (report to their maintainers)
* Self-hosted deployments with custom modifications

---

## Security Practices

While this is a hobby project, reasonable precautions are taken:

* Dependencies are periodically updated
* Basic input validation and authentication controls are implemented
* Secrets are not stored in the repository

That said, **no guarantees are made regarding security**. Users should:

* Deploy behind appropriate infrastructure (e.g. firewalls, TLS)
* Monitor their own environments
* Perform independent security reviews before production use

---

## Legal

This project is provided “as is” without warranty of any kind. By reporting vulnerabilities, you agree to act in good faith and avoid:

* Data destruction
* Service disruption
* Accessing other users' data

---

## Acknowledgements

Thanks to everyone who responsibly reports security issues and helps improve the project.
