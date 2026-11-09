#!/usr/bin/env bash
# Merge the current feature branch into main (fast-forward only) and push main.
# Aborts if main has moved on; use g_merge_feature.sh in that case.
set -euo pipefail

main_branch="main"

git rev-parse --is-inside-work-tree >/dev/null
current_branch="$(git branch --show-current)"

if [[ -z "$current_branch" ]]; then
    echo "Error: not on a branch (detached HEAD)." >&2
    exit 1
fi
if [[ "$current_branch" == "$main_branch" ]]; then
    echo "Error: you are on '$main_branch'. Switch to the feature branch first." >&2
    exit 1
fi

read -r -p "Merge feature branch '$current_branch' into '$main_branch'? [y/N] " answer
[[ "$answer" =~ ^[yYjJ]$ ]] || { echo "Aborted."; exit 1; }

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree has uncommitted changes. Run g_push_feature.sh first." >&2
    git status --short
    exit 1
fi

echo ">>> Updating '$main_branch' from GitHub"
git switch "$main_branch"
git pull --ff-only

echo ">>> Fast-forward merging '$current_branch' into '$main_branch'"
if ! git merge --ff-only "$current_branch"; then
    echo "Error: fast-forward not possible, '$main_branch' has new commits." >&2
    echo "Use g_merge_feature.sh to rebase the feature branch onto '$main_branch' first." >&2
    git switch "$current_branch"
    exit 1
fi

echo ">>> Pushing '$main_branch' to GitHub"
git push

echo "Done. You are now on '$main_branch'."
echo "Run 'g_clean_feature.sh $current_branch' to delete the feature branch."
