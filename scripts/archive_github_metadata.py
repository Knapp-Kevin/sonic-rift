"""Create a non-destructive, verifiable archive of GitHub repo metadata.

This is not a Git mirror, issue importer, or reversible fork-detachment mechanism.
All network requests are GET. Keep the output private: issues/reviews may include
personal information and secrets that contributors inadvertently posted.

Example:
    GH_TOKEN=... python scripts/archive_github_metadata.py \
      Knapp-Kevin/sonic-rift --output ../sonic-rift-metadata-archive
    python scripts/archive_github_metadata.py --verify ../sonic-rift-metadata-archive
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NEXT_PATTERN = re.compile(r'<([^>]+)>;\s*rel="next"')
COLLECTIONS = ("issues", "pulls", "labels", "milestones", "releases", "branches", "tags")
ISSUE_DETAILS = ("comments", "events", "timeline")
PR_DETAILS = ("reviews", "comments", "commits", "files")


def canonical_json(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(root, relative_path, data, manifest):
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_json(data)
    target.write_bytes(content)
    manifest["files"][str(relative_path).replace("\\", "/")] = {
        "sha256": hashlib.sha256(content).hexdigest(),
        "count": len(data) if isinstance(data, list) else 1,
    }


def parse_next(header):
    match = NEXT_PATTERN.search(header or "")
    return match.group(1) if match else None


class GitHubReader:
    def __init__(self, token, opener=urlopen, api_root=API_ROOT):
        self._token = token
        self._opener = opener
        self._root = api_root.rstrip("/")

    def get(self, resource, params=None):
        """Fetch complete paginated REST results, fail closed on any failed page."""
        url = f"{self._root}{resource}"
        if params:
            url += "?" + urlencode(params)
        output = []
        paginated = False
        while url:
            if not url.startswith(self._root + "/"):
                raise RuntimeError("Refusing unexpected pagination host")
            headers = {"Accept": "application/vnd.github+json",
                       "X-GitHub-Api-Version": "2022-11-28",
                       "User-Agent": "SonicRift-metadata-archive"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            req = Request(url, headers=headers, method="GET")
            try:
                with self._opener(req, timeout=30) as response:
                    data = json.load(response)
                    next_url = parse_next(response.headers.get("Link", ""))
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                # Avoid response bodies and Authorization headers in exceptions.
                code = getattr(exc, "code", None)
                raise RuntimeError(f"GitHub GET failed ({'HTTP ' + str(code) if code else type(exc).__name__}); archive incomplete") from None
            if isinstance(data, list):
                output.extend(data)
                paginated = True
            elif not paginated and next_url is None:
                return data
            else:
                raise RuntimeError("Unexpected GitHub pagination response shape")
            url = next_url
        return output


def collect(repo, destination, reader):
    """Collect independent machine-readable snapshots without mutating GitHub."""
    if not REPO_PATTERN.fullmatch(repo):
        raise ValueError("Expected OWNER/REPOSITORY")
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError("Archive destination is not empty; choose a new directory")
    root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        root.chmod(0o700)
    escaped = "/".join(quote(part, safe="") for part in repo.split("/"))
    prefix = f"/repos/{escaped}"
    manifest = {"schema_version": 1, "repo": repo, "files": {}, "totals": {},
                "limitations": [
                    "Metadata snapshot only: NOT a Git mirror or a restore operation",
                    "Binary release assets, wiki pages, attachments, secrets, Actions settings, stars, watchers, and child forks are not backed up",
                    "Review discussions and issues may contain private or sensitive information; keep this folder private",
                    "The snapshot is not atomic; concurrent repository activity can change records while exporting",
                ]}
    metadata = reader.get(prefix)
    write_json(root, Path("repository.json"), metadata, manifest)
    collections = {}
    for name in COLLECTIONS:
        params = {"per_page": 100}
        if name in ("issues", "pulls", "milestones"):
            params["state"] = "all"
        objects = reader.get(f"{prefix}/{name}", params)
        if not isinstance(objects, list):
            raise RuntimeError(f"Unexpected response from {name}")
        collections[name] = objects
        manifest["totals"][name] = len(objects)
        write_json(root, Path("collections") / f"{name}.json", objects, manifest)

    for issue in collections["issues"]:
        number = int(issue["number"])
        base = f"{prefix}/issues/{number}"
        for name in ISSUE_DETAILS:
            objects = reader.get(f"{base}/{name}", {"per_page": 100})
            write_json(root, Path("issue-details") / str(number) / f"{name}.json", objects, manifest)

    for pr in collections["pulls"]:
        number = int(pr["number"])
        base = f"{prefix}/pulls/{number}"
        for name in PR_DETAILS:
            objects = reader.get(f"{base}/{name}", {"per_page": 100})
            write_json(root, Path("pr-details") / str(number) / f"{name}.json", objects, manifest)

    # Write manifest LAST. Its existence means that every page finished, not
    # that the archive is restorable or that current GitHub data is unchanged.
    (root / "manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def verify(directory):
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        path = root / name
        if path.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError("Unsafe archive path")
        if not path.is_file():
            raise FileNotFoundError(f"Missing archive entry: {name}")
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != expected["sha256"]:
            raise ValueError(f"Archive checksum mismatch: {name}")
        actual = json.loads(blob)
        count = len(actual) if isinstance(actual, list) else 1
        if count != expected["count"]:
            raise ValueError(f"Archive item count mismatch: {name}")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", help="GitHub OWNER/REPOSITORY")
    parser.add_argument("--output", type=Path, help="Private directory outside the repository")
    parser.add_argument("--verify", metavar="DIRECTORY", type=Path, help="Verify a completed archive offline")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify(args.verify)
        print(f"Verified {len(result['files'])} archived JSON entries for {result['repo']}")
        return 0
    if not args.repository or not args.output:
        parser.error("Repository and --output are required for an export")
    if not os.environ.get("GH_TOKEN"):
        parser.error("Set GH_TOKEN with permission to read the repository")
    result = collect(args.repository, args.output, GitHubReader(os.environ["GH_TOKEN"]))
    verify(args.output)
    print(f"Archived {len(result['files'])} JSON entries for {result['repo']}; checksum verification passed")
    print("Also make a separate Git mirror and release-asset backup. Do NOT detach based on this archive alone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
