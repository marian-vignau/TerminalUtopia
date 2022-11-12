#!/usr/bin/python3
"""
Hard link and create a repository of configuration files.

"""

import argparse
import os
import subprocess
import shutil

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


ENV_VAR = "CONFIG_REPO_PATH"
CONFIG_REPO_PATH = os.environ.get(ENV_VAR)
if not CONFIG_REPO_PATH:
    # if not setted, use the program's default.
    CONFIG_REPO_PATH = "~/.local/config-repo/dotfiles"
see_time = lambda x: datetime.fromtimestamp(x.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


class Task:
    def __init__(self, args):
        self.args = args
        self._repo_path = None
        self._home_path = Path.home()
        self._file_path = None
        operations = {}
        for op in ["restore", "add", "compare"]:
            arg = getattr(self.args, op + "_filename")
            if arg:
                self.operation, self._file = op, arg
                operations[op] = arg
        if len(operations) > 1:
            raise ValueError("You must add, compare OR restore, only one of them.")

    @property
    def repo_path(self):
        """Search dot file repository path.

        Try using command line argument or defaults to enviroment variable."""
        if not self._repo_path:
            new_path = self.args.path or CONFIG_REPO_PATH
            self._repo_path = Path(new_path.strip()).expanduser().resolve()
            if not self._repo_path.exists():
                raise FileNotFoundError(f"Repository directory not founded. {str(new_path)}")
            self.logger(reason="Repo path", objec=self._repo_path)
        return self._repo_path

    @property
    def home_path(self):
        if not self._home_path.exists():
            raise FileNotFoundError("Home directory not detected.")
        return self._home_path

    @property
    def file_path(self):
        """File path have to be inside repository dir or user's home dir."""
        if not self._file_path:
            file = self._file
            self._file_path = Path(file).expanduser().resolve()
            if self._file_path in [self.repo_path, self.home_path]:
                self.relative_to = self._file_path
            elif self.repo_path in self._file_path.parents:
                self.relative_to = self.repo_path
            elif self.home_path in self._file_path.parents:
                self.relative_to = self.home_path
            else:
                raise FileNotFoundError(f"Not relative to config nor home {file}")
            self.logger(reason="File path", objec=self._file_path)
            self.logger(reason="Relative to", objec=self.relative_to)
        return self._file_path

    def run(self):
        """Do the task."""
        comparables = []
        if self.file_path.is_dir():
            files = [p for p in self.file_path.rglob("*") if not p.is_dir()]
        else:
            files = [self.file_path]
        for filepath in files:
            filename = filepath.relative_to(self.relative_to)
            orig, dest = self.get_orig_dest(filename)
            status = self._check_file(orig, dest)
            if self.operation == "compare":
                if status[1] == "E!":
                    self.logger(status=status)
                if "DIFFERENT" in status[0]:
                    comparables.append((orig, dest))
            else:
                if not self.args.dry:
                    status = self._link_file(orig, dest, filename)
                self.logger(status=status)

        if len(comparables) == 1:
            orig, dest = comparables[0]
            subprocess.run(args=["delta", str(orig), str(dest)])

        if len(files) > 1:
            self.logger(reason="Total files", objec=len(files))

    def logger(self, status=None, reason="", objec=""):
        """Explain user what is happening."""
        def str_path(path):
            path = str(path)
            path = path.replace(str(self.repo_path), "<repo>")
            path = path.replace(str(self.home_path), "     ~")
            return path

        if self.args.quiet:
            return
        elif self.args.verbose:
            if any((reason, objec)):
                print(f"{str(reason)}: {str(objec)}")
        if status:
            msg, tag, orig, dest = status
            if self.args.verbose or self.operation == "compare":
                comp = [f"{see_time(path)} {str_path(path)}" for path in [orig, dest] if path.exists()]
                comp.sort()
                output = f"{tag} {msg}\n" + "\n".join(comp)
            else:
                path = orig if orig.exists() else dest
                output = f"{tag}: {str_path(path)}   - {msg}"
            print(output)

    def get_orig_dest(self, filename):
        """Get the origin and destiny filenames."""
        home_ln = self.home_path.joinpath(str(filename))
        repo_ln = self.repo_path.joinpath(str(filename))
        if self.operation == "restore":
            return repo_ln, home_ln
        return home_ln, repo_ln

    def _check_file(self, orig, dest):
        """Check status."""
        if not orig.exists():
            return "NOT FOUND", "E!", orig, dest
        if not dest.exists():
            return "MISSING FILE", "E!", orig, dest
        if os.path.samefile(orig, dest):
            return "HARDLINKED", "==", orig, dest
        else:
            return "DIFFERENT FILES", "E!", orig, dest

    def _link_file(self, orig, dest, filename):
        """Actually create the link."""
        if dest.exists():
            if self.args.overwrite:
                dest.unlink()
                os.link(orig, dest)
                status = ("OVERWRITED", ">>", orig, dest)
            else:
                return "DIFFERENT FILES", "E!", orig, dest
        else:
            if len(filename.parts) > 1:
                to_path = Path(*dest.parts[:-1])
                to_path.mkdir(parents=True, exist_ok=True)
            os.link(orig, dest)
            status = ("LINKED", "=>", orig, dest)
        if dest.exists():
            return status
        return "FILE SYSTEM ERROR", "E!", orig, dest


def parse():
    """Get the command line arguments and parses them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-a", "--add_filename", type=str, help="The file or folder that should be added", required=False
    )
    parser.add_argument(
        "-r", "--restore_filename", type=str, help="The file or folder that should be restored", required=False
    )
    parser.add_argument("-c", "--compare_filename", type=str, help="The file that should be compared", required=False)
    parser.add_argument(
        "-p", "--path", type=str, help=f"use custom repository path instead of {CONFIG_REPO_PATH}", required=False
    )
    parser.add_argument("-R", "--dry", action="store_true", help="just show what will do")
    parser.add_argument("-v", "--verbose", action="store_true", help="show verbose result")
    parser.add_argument("-q", "--quiet", action="store_true", help="don't show results")
    parser.add_argument("-o", "--overwrite", action="store_true", help="overwrite destiny if exists")

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse()
    task = Task(args=args)
    task.run()
