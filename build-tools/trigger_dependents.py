#!/usr/bin/env python

import os
import subprocess
from typing import List, Set

root_dir: str = os.environ.get("BUILDKITE_BUILD_CHECKOUT_PATH")


def _full_path(subdirectory: str) -> str:
    return root_dir + '/' + subdirectory


def find_dependents(subdirectory: str, dependencies: List[str]) -> Set[str]:
    dependents: Set[str] = set()
    list_of_files = os.listdir(_full_path(subdirectory))
    for entry in list_of_files:
        full_entry_path: str = _full_path(subdirectory + '/' + entry)
        if os.path.isdir(full_entry_path):
            dependents = dependents.union(find_dependents(full_entry_path, dependencies))
            continue
        dependencies_file: str = full_entry_path + '/dependencies.txt'
        if not os.path.isfile(dependencies_file):
            continue
        with open(dependencies_file, 'r') as file1:
            for line in file1:
                if '#' in line:
                    i = line.index("#")
                    line = line[0:i]
                line = line.strip()
                if not line:
                    continue
                if line in dependencies:
                    dependents.add(subdirectory)
    return dependents


def get_bk_steps(this_build:str, dependents: Set[str]) -> str:
    steps = f"steps:\n"
    for dep in dependents:
        dep = dep.replace('/', '-')
        steps += f"""
  - trigger: {dep}
    async: true
    build:
      env:
        DEPENDENCY_TRIGGER: {this_build}
"""
    return steps

def upload_bk_steps(steps: str):
    subprocess.run(['buildkite-agent', 'pipeline', 'upload'], input=steps, text=True)


def main() -> None:
    this_build: str = os.environ.get("BUILDKITE_PIPELINE_NAME")
    # Splitting on regex might be better here
    just_published_dependencies: List[str] = os.environ.get("PUBLISHED_DEPENDENCIES").split()
    dependents: Set[str] = find_dependents(root_dir, just_published_dependencies)
    if not dependents:
        print("No dependent components found.")
        return
    steps: str = get_bk_steps(this_build, dependents)
    upload_bk_steps(steps)


if __name__ == '__main__':
    main()