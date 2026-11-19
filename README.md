# Repo Publication Guard

A small, practical, **zero-runtime-dependency** Python command-line tool that helps developers check a repository **before making it public**.

Its two jobs are:

1. **Repository preflight:** flag common credential signatures and risky tracked paths without printing secret values.
2. **Environment-key drift:** compare variable *names* in `.env.example` and `.env`, without exposing values.

Works locally, offline, with Python 3.10+. It never uploads source code or calls a third-party service.

> **Security limits:** This is a best-effort heuristic, not a comprehensive secret scanner or proof that a repository is safe. It can miss secrets and produce false positives. If any actual credential has been committed or exposed, rotate/revoke it; deleting the file alone does not remove it from Git history.

## Install

```sh
python -m pip install -e .
```

Or run directly without installation:

```sh
PYTHONPATH=src python -m repo_publication_guard scan . --mode all
```

## Usage

```sh
# Check Git-tracked files (recommended before publication):
repo-guard scan .

# Check files in the Git index, useful before committing:
repo-guard scan . --mode staged

# Scan all local files (including untracked files; no network):
repo-guard scan . --mode all

# Return structured findings for CI automation:
repo-guard scan . --format json

# Check environment key names; values are NEVER displayed:
repo-guard env --template .env.example --file .env

# Fail CI on medium or high findings instead of only high:
repo-guard scan . --fail-on medium
```

Exit codes: `0` = no findings at or above configured threshold, `1` = threshold met, `2` = input or environment error.

The scan detects selected AWS, GitHub, OpenAI, Google, and Slack key formats; private-key headers; some literal credential assignments; and risky file paths such as `.env`, private credential stores, and Terraform state. It emits **only rule identifiers, file locations, and generic messages**.

## Example (no real credentials)

```sh
repo-guard env --template .env.example --file .env
# [high] .env: MISSING_KEY — Key required by template is missing: SERVICE_API_KEY
```

The tool treats all template key names as required. It does not evaluate dotenv expressions, variable expansion, or application-specific configuration semantics.

## How it differs from full secret scanners

Repo Publication Guard is intentionally small, privacy-preserving, dependency-free, and easy to audit. It is appropriate as an extra local/CI check, **not a replacement** for tools such as Gitleaks or GitHub secret scanning. Patterns are intentionally explicit; the scanner does not send files to an AI model.

## Development

```sh
python -m unittest discover -s tests -v
python -m compileall -q src
```

The `.github/workflows/ci.yml` example runs unit tests on Python 3.10 and 3.13, followed by a tracked-file scan. It only runs after a repository is pushed to GitHub.

## Security and contributing

See [SECURITY.md](SECURITY.md) for disclosure guidance and [CONTRIBUTING.md](CONTRIBUTING.md) for tests and contributor instructions. Please do **not** include real tokens or secrets in issue reports, fixtures, or pull requests.

## License

MIT (see [LICENSE](LICENSE)).
