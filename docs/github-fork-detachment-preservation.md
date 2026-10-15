# GitHub fork-network preservation: pre-detachment gate

**Status: Preparation only. Detachment is NOT authorized.**

Sonic Rift is currently a public, ~10 MB GitHub repository, still in the AcTePuKc/Chatterbox-TTS-UI fork network. Its GitHub REST metadata showed **zero child forks** at this checkpoint, which suggests the self-service Leave fork network control may be eligible. GitHub's official requirements are a public repository, under 1 GB and no child forks; GitHub settings are authoritative at execution time. **Do not click the control yet.**

GitHub's documentation warns that leaving a fork network preserves Git commits but **does not retain issues, pull requests, comments, wikis, stars, watchers, child forks or other associated metadata**; the operation is permanent. Maintaining an independent Sonic Rift product does not require performing this destructive hosting operation, and changing the GitHub fork relationship **does not erase the licenses of inherited source code**.

Reference: https://docs.github.com/en/pull-requests/how-tos/work-with-forks/detaching-a-fork

## Read-only metadata export

Run this from a Python 3.11+ installation on a trusted machine with a GitHub token that can read the repository. All HTTP calls are GET requests, and the tool never executes git push, deletes resources or calls a GitHub mutation endpoint.

**Windows PowerShell, with authenticated GitHub CLI:**

~~~powershell
# Execute from the Sonic Rift repo checkout. The output must be OUTSIDE the repo.
$env:GH_TOKEN = gh auth token
python scripts/archive_github_metadata.py Knapp-Kevin/sonic-rift --output ../sonic-rift-fork-snapshot-20261015
python scripts/archive_github_metadata.py --verify ../sonic-rift-fork-snapshot-20261015
Remove-Item Env:GH_TOKEN
~~~

The tool reads repository metadata, all issues and PRs (open and closed), issue comments/events/timeline, PR reviews/review comments/commits/files, labels, milestones, releases, branches and tags. It paginates GitHub REST responses and refuses to overwrite an existing nonempty directory. A manifest is only written after every request completes; --verify checks each saved JSON file's checksum and item count. A failed run is **partial**, not a valid archival copy. **Never commit the output to GitHub**: it may contain sensitive discussion content or personal information.

The Python exporter archives JSON *metadata*, **not** everything necessary to recreate the current GitHub collaboration history. Comment authors, stable issue/PR numbers, review identities, signatures, stars, followers, discussion threads, webhooks, or original URLs generally cannot be perfectly restored into a newly created repository. A saved snapshot provides audit/reference evidence, not a lossless importer.

## Separate Git and release backups

From the same machine, create a separate bare Git mirror in a private local directory:

~~~powershell
git clone --mirror https://github.com/Knapp-Kevin/sonic-rift.git ../sonic-rift-fork-git-mirror.git
git --git-dir=../sonic-rift-fork-git-mirror.git fsck --full
~~~

Use gh release list / gh release download or an independently checked release-asset export for every distributed binary. Preserve version tags, checksums, build instructions and Git LFS objects separately if used. The metadata exporter records release JSON but **does not download release binaries**. Also document externally managed secrets, webhooks, GitHub Projects, branch protection, environments and deployment settings: these are not in the export. The repository currently advertises GitHub Projects enabled and its topics/description still contain legacy branding.

## Acceptance before any irreversible action

- [ ] The owner explicitly requests network detachment, with an understood loss-of-metadata tradeoff.
- [ ] PR #24 Live Voice and every other active workstream has an agreed disposition, with exact commits and artifacts in main or separately preserved.
- [ ] The full JSON export finishes and --verify succeeds; issue/PR counts are compared with current GitHub API results, taking concurrency into account.
- [ ] The Git mirror passes git fsck, release binaries/assets and any Git LFS data are independently backed up, and restore procedures are dry-run tested.
- [ ] Issue, PR, review and discussion references that are important to project governance are captured in a permanent searchable index; expected broken links/ID changes are documented.
- [ ] Repository administration, branch policies, Actions settings, project boards and any external integration are inventoried with approved reconstruction steps.
- [ ] Source-code provenance and original license notices have been independently reconciled. The owner has separately chosen a license for the source code they own; all retained third-party notices stay intact.
- [ ] GitHub Settings shows the leave-network control is actually available; repository eligibility and impact are re-verified immediately before execution.
- [ ] A rollback/recovery plan exists for *files and references*, without falsely claiming the GitHub metadata itself is recoverable.
- [ ] Owner gives a second, explicit, time-specific GO to detach.

**Current decision: HOLD.** Proceed with product engineering, licensing inventory and metadata preservation. Do not delete or detach this repository as part of routine refactoring.
