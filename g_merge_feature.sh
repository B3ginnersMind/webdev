#!/usr/bin/env bash
# Rebase the current feature branch onto the latest main, then merge it into
# main (fast-forward) and push both branches.
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

read -r -p "Rebase '$current_branch' onto '$main_branch' and merge it? [y/N] " answer
[[ "$answer" =~ ^[yYjJ]$ ]] || { echo "Aborted."; exit 1; }

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree has uncommitted changes. Run g_push_feature.sh first." >&2
    git status --short
    exit 1
fi

echo ">>> Updating '$main_branch' from GitHub"
git switch "$main_branch"
git pull --ff-only
git switch "$current_branch"

echo ">>> Rebasing '$current_branch' onto '$main_branch'"
if ! git rebase "$main_branch"; then
    echo "Error: rebase stopped because of conflicts." >&2
    echo "Resolve them, then 'git add <files>' and 'git rebase --continue'," >&2
    echo "or cancel with 'git rebase --abort'. Afterwards run this script again." >&2
    exit 1
fi

# The rebase rewrote the branch history, so an already pushed branch needs a force push.
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    echo ">>> Updating '$current_branch' on GitHub (force-with-lease after rebase)"
    git push --force-with-lease
fi

echo ">>> Fast-forward merging '$current_branch' into '$main_branch'"
git switch "$main_branch"
git merge --ff-only "$current_branch"

echo ">>> Pushing '$main_branch' to GitHub"
git push

echo "Done. You are now on '$main_branch'."
echo "Run 'g_clean_feature.sh $current_branch' to delete the feature branch."
