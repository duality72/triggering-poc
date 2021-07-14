#!/usr/bin/env python

import os
import re
import subprocess
from typing import List, Set, Tuple, Dict

root_dir: str = os.environ.get("BUILDKITE_BUILD_CHECKOUT_PATH")
debug: bool = os.environ.get("DEBUG_OUTPUT", 'false').lower() == 'true'
all_cluster_members: Dict[str, str] = {}


def _debug(output: str) -> None:
    if not debug:
        return
    print("--- " + output)

def _full_path(subdirectory: str) -> str:
    return root_dir + '/' + subdirectory


def find_dependents(subdirectory: str, published_dependencies: List[str]) -> Set[str]:
    dependents: Set[str] = set()
    _debug(f"Finding dependents in {subdirectory}")
    clusters_file_path: str = subdirectory + "/clusters.txt"

    if os.path.isfile(clusters_file_path):
        _debug(f"...reading clusters in {clusters_file_path}")
        with open(clusters_file_path, 'r') as clusters_file:
            for line in clusters_file:
                if '#' in line:
                    i = line.index("#")
                    line = line[0:i]
                line = line.strip()
                if not line:
                    continue
                if '=' not in line:
                    _debug(f"...bad cluster line! -> {line}")
                cluster_name: str
                cluster_members: Tuple[str]
                cluster_name, *cluster_members, = re.split(r'[=,\s]', line)
                for member in cluster_members:
                    if member in all_cluster_members:
                        _debug(f"...{member} is already in a cluster!")
                        exit(1)
                    all_cluster_members[member] = f"cluster/{cluster_name}"
                    if cluster_name in published_dependencies

    list_of_files = os.listdir(_full_path(subdirectory))
    for entry in list_of_files:
        if entry == '.git':
            continue
        subdirectory_entry = subdirectory + '/' + entry if subdirectory else entry
        full_entry_path: str = _full_path(subdirectory_entry)
        if os.path.isdir(full_entry_path):
            dependents = dependents.union(find_dependents(subdirectory_entry, published_dependencies))
            continue
        if entry != "dependencies.txt":
            continue
        _debug("...checking dependencies file")
        with open(full_entry_path, 'r') as file1:
            for line in file1:
                if '#' in line:
                    i = line.index("#")
                    line = line[0:i]
                line = line.strip()
                if not line:
                    continue
                if line in all_cluster_members:
                    _debug(f"...checking if {line}'s cluster was published")
                    if all_cluster_members[line] in published_dependencies:
                        _debug(f"...adding dependent {subdirectory}")
                        dependents.add(subdirectory)
                    continue
                _debug(f"...checking if {line} is one of the published dependencies")
                if line in published_dependencies:
                    if subdirectory in all_cluster_members:
                        _debug(f"...{subdirectory} is part of a cluster. Adding dependent {all_cluster_members[subdirectory]}")
                        dependents.add(all_cluster_members[subdirectory])
                        continue
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
