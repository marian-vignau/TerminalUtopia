#!/usr/bin/env python3

"""Download the last release from a github repository.

"""
import argparse
import json
import sys
import urllib.request


class Download:
    def _search(self, _json, charact):
        for asset in _json["assets"]:
            if all([ch.lower().strip() in asset["name"].lower() for ch in charact]):
                return asset
        return None

    def _get_assets(self, author, repo):
        _json = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.github.com/repos/{author}/{repo}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
            ).read()
        )
        return _json

    def _download(self, url, name):
        print(f"Donwload {name} from {url}")
        urllib.request.urlretrieve(url, name)

        return url, name

    def get(self, author, repo, charact=None):
        _json = self._get_assets(author, repo)
        if not _json:
            return FileNotFoundError("Could'nt find resources.")
        filtre = [f.strip().lower() for f in charact]
        asset = self._search(_json, filtre)
        if not asset:
            return FileNotFoundError("Couldn't find download with characteristics" + "; ".join(charact))
        return self._download(asset["browser_download_url"], asset["name"])


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("owner", type=str, help="the owner of the project repo")
parser.add_argument("repo", type=str, help="the project repository")
parser.add_argument("--filter", "-f", nargs="*")

args = parser.parse_args()

if not args.owner or not args.repo:
    ValueError("Need repo name and owner")
filt = args.filter
if not filt:
    filt = [args.repo, "linux", "x86_64", "tar.gz"]
print(f"Searching for {';'.join(filt)}...")

dwn = Download().get(args.owner, args.repo, filt)
