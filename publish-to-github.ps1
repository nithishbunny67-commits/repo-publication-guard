# Publishes ONLY this standalone project as a new, public GitHub repository.
# Review this script before running it. It never touches APEX DEALFLOW.
$ErrorActionPreference = 'Stop'
$ExpectedUser = 'nithishbunny67-commits'
$RepoName = 'repo-publication-guard'
$FullName = "$ExpectedUser/$RepoName"

Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath './pyproject.toml') -or
    -not (Test-Path -LiteralPath './src/repo_publication_guard/scanner.py')) {
    throw 'Run from the standalone repo-publication-guard project. Expected files are missing.'
}
if (Test-Path -LiteralPath './.git') {
    throw 'This directory already has a Git repository. Stopping to prevent accidental publication.'
}
foreach ($tool in @('git', 'gh', 'python')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Missing '$tool'. Install it before publishing."
    }
}

gh auth status
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub CLI is not authenticated. Run: gh auth login'
}
$AuthenticatedUser = (gh api user --jq '.login').Trim()
if ($LASTEXITCODE -ne 0 -or $AuthenticatedUser -ne $ExpectedUser) {
    throw "Wrong GitHub account. Expected $ExpectedUser; current: $AuthenticatedUser"
}
# GitHub CLI refuses to create an existing repository; it will not overwrite one.

Write-Host "About to publish a NEW PUBLIC repository: https://github.com/$FullName"
Write-Host 'All tracked files from THIS directory will be visible to everyone.'
$Confirmation = Read-Host 'Type PUBLISH to continue'
if ($Confirmation -cne 'PUBLISH') {
    Write-Host 'Cancelled; nothing published.'
    exit 1
}

python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed. Publication stopped.' }
$env:PYTHONPATH = 'src'
python -m repo_publication_guard scan . --mode all --fail-on high
if ($LASTEXITCODE -ne 0) { throw 'Publication scan failed. Publication stopped.' }


git init -b main
if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
git add .
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
Write-Host 'Files about to be committed:'
git status --short
python -m repo_publication_guard scan . --mode staged --fail-on high
if ($LASTEXITCODE -ne 0) { throw 'Staged-file scan failed. Publication stopped.' }
git commit -m 'Initial open-source release: repository publication guard'
if ($LASTEXITCODE -ne 0) { throw 'git commit failed. Configure git user.name and user.email if necessary.' }

gh repo create $FullName --public --source . --remote origin --push --description 'Dependency-free privacy-first checks for repository publication'
if ($LASTEXITCODE -ne 0) { throw 'GitHub repository creation/push failed.' }
gh repo view $FullName --json nameWithOwner,visibility,url --jq '{name: .nameWithOwner, visibility: .visibility, url: .url}'
Remove-Item Env:PYTHONPATH
