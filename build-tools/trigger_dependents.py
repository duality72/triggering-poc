#!/usr/bin/env python

import os
import subprocess
from typing import List, Set

root_dir: str = os.environ.get("BUILDKITE_BUILD_CHECKOUT_PATH")
debug: bool = os.environ.get("DEBUG_OUTPUT", 'false').lower() == 'true'


def _debug(output: str) -> None:
    if not debug:
        return
    print("--- " + output)

def _full_path(subdirectory: str) -> str:
    return root_dir + '/' + subdirectory


def find_dependents(subdirectory: str, published_dependencies: List[str]) -> Set[str]:
    _debug(f"Finding dependents in {subdirectory}")
    dependents: Set[str] = set()
    list_of_files = os.listdir(_full_path(subdirectory))
    for entry in list_of_files:
        if entry == '.git':
            continue
        subdirectory_entry = subdirectory + '/' + entry if subdirectory else entry
        full_entry_path: str = _full_path(subdirectory_entry)
        if os.path.isdir(full_entry_path):
            dependents = dependents.union(find_dependents(subdirectory_entry, published_dependencies))
            continue
        _debug("...checking dependencies file")
        if entry != "dependencies.txt":
            continue
        with open(full_entry_path, 'r') as file1:
            for line in file1:
                if '#' in line:
                    i = line.index("#")
                    line = line[0:i]
                line = line.strip()
                if not line:
                    continue
                _debug(f"...checking if {line} is one of the published dependencies")
                if line in published_dependencies:
                    _debug(f"...adding dependent {subdirectory}")
                    dependents.add(subdirectory)
    return dependents


def get_bk_steps(this_build:str, dependents: Set[str]) -> str:
    _debug(f"Generating dependent trigger steps for {this_build}")
    steps = f"steps:\n"
    for dep in dependents:
        _debug(f"...adding trigger step for {dep}")
        dep = dep.replace('/', '-').lower()
        steps += f"""
  - trigger: {dep}
    async: true
    build:
      env:
        DEPENDENCY_TRIGGER: {this_build}
"""
    return steps

def upload_bk_steps(steps: str):
    subprocess.run(['buildkite-agent', 'pipeline', 'upload'], input=steps, text=True, check=True)


def main() -> None:
    this_build: str = os.environ.get("PUBLISHED_BUILD")
    # Splitting on regex might be better here
    just_published_dependencies: List[str] = os.environ.get("PUBLISHED_DEPENDENCIES").split()
    dependents: Set[str] = find_dependents('', just_published_dependencies)
    if not dependents:
        print("No dependent components found.")
        return
    steps: str = get_bk_steps(this_build, dependents)
    upload_bk_steps(steps)


if __name__ == '__main__':
    main()
