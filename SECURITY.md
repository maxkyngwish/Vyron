# Security policy

VYRON runs as a normal user, keeps everything local and never disables security
features.

## Reporting a vulnerability

Please open a **private security advisory** on GitHub (Security → Advisories) or
contact the maintainer directly. Do not open a public issue for a vulnerability.

Include the affected version, Windows build, reproduction steps and impact.

## Scope

In scope:

- privilege escalation or writing outside the user's own profile;
- persistent changes that are not restored;
- leaking local account data or settings;
- command injection through game names, paths or registry values;
- crashes caused by malformed input files.

Out of scope:

- FPS or ping results (they depend on hardware and network);
- Windows SmartScreen warnings on the unsigned executable;
- changes made by other software while VYRON runs.

## Design guarantees

- No telemetry, no remote accounts, no auto-update calls.
- Passwords: PBKDF2-HMAC-SHA256 with a random salt; clear text is never stored.
- Registry writes are limited to `HKCU` and always reversible.
- No `REALTIME_PRIORITY_CLASS`, no security-service tampering, no automatic
  process termination.
