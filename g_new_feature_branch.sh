#!/usr/bin/env bash
# Create a new feature branch from the latest state of main and switch to it.
# Usage: g_new_feature_branch.sh <branch-name>
set -euo pipefail

main_branch="main"

if [[ $# -ne 1 || -z "$1" ]]; then
    echo "Usage: $(basename "$0") <branch-name>" >&2
    exit 1
fi
feature_branch="$1"

git rev-parse --is-inside-work-tree >/dev/null

if ! git check-ref-format --branch "$feature_branch" >/dev/null 2>&1; then
    echo "Error: '$feature_branch' is not a valid branch name." >&2
    exit 1
fi

if git show-ref --verify --quiet "refs/heads/$feature_branch"; then
    echo "Error: branch '$feature_branch' already exists locally." >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree has uncommitted changes. Commit or stash them first." >&2
    git status --short
    exit 1
fi

echo ">>> Updating '$main_branch' from GitHub"
git switch "$main_branch"
git pull --ff-only

echo ">>> Creating and switching to '$feature_branch'"
git switch -c "$feature_branch"

echo "Done. You are now on '$feature_branch' (based on $(git rev-parse --short HEAD))."
