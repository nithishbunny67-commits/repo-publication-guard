# Publish this new project on GitHub

The project is **independent of APEX DEALFLOW**. It contains synthetic tests only, no credentials and no APEX data. Do not copy files from private projects into this repository.

## Windows PowerShell (recommended)

1. Extract the ZIP into a fresh directory.
2. Open PowerShell inside `repo-publication-guard`.
3. Review `publish-to-github.ps1` with a text editor.
4. Run:

```powershell
gh auth status
.\publish-to-github.ps1
```

If GitHub CLI is not authenticated, first run `gh auth login` and try again. The script checks that you are signed in as `nithishbunny67-commits`, runs tests, scans files, asks you to type `PUBLISH`, then creates a **public** repository and pushes the initial commit. It aborts if the destination repository already exists. If local PowerShell policy prevents running the script, you can use the manual alternative below rather than changing your system's policy.

## Manual alternative

```powershell
# From the extracted project folder, after reviewing all files:
python -m unittest discover -s tests -v
$env:PYTHONPATH = 'src'
python -m repo_publication_guard scan . --mode all
Remove-Item Env:PYTHONPATH

git init -b main
git add .
git commit -m 'Initial open-source release'
gh auth login  # only if you have not already signed in
gh repo create nithishbunny67-commits/repo-publication-guard --public --source . --remote origin --push
```

If `git commit` asks you to configure a Git author, set your own name and email using `git config --global user.name` and `git config --global user.email` and try again.

## After publishing

- Verify that the new repository is public at `https://github.com/nithishbunny67-commits/repo-publication-guard`.
- Enable GitHub's security advisories/private vulnerability reporting if available for the repository.
- Invite legitimate feedback, accept improvements, respond to real issues, and maintain useful releases.
- Do not purchase stars, invent usage statistics, or claim adoption the project does not have.

A newly created repository **does not automatically qualify** for OpenAI's Codex for Open Source program. OpenAI considers meaningful usage, ecosystem importance, and real maintainer activity. Apply only with accurate details about the project's actual progress.
