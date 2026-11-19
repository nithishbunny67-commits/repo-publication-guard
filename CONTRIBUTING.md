# Contributing

Useful contributions include false-positive improvements, additional privacy-preserving detection rules, performance fixes, and portability tests.

1. Create a focused issue or pull request describing behavior and a minimal **synthetic** reproduction.
2. Keep the runtime dependency-free.
3. Add or update unit tests. Test credentials must be synthetic and must not authenticate to any service.
4. Run `python -m unittest discover -s tests -v` before opening a PR.
5. Avoid introducing telemetry or sending repository contents over a network.

All contributors should be respectful and act in good faith.
