#!/usr/bin/env bash
# Commit all changes on the current feature branch and push it to GitHub.
# Usage: g_push_feature.sh ["commit message"]
set -euo pipefail

main_branch="main"

git rev-parse --is-inside-work-tree >/dev/null
current_branch="$(git branch --show-current)"

if [[ -z "$current_branch" ]]; then
    echo "Error: not on a branch (detached HEAD)." >&2
    exit 1
fi
if [[ "$current_branch" == "$main_branch" ]]; then
    echo "Error: you are on '$main_branch'. This script is meant for feature branches." >&2
    exit 1
fi

read -r -p "Current branch is '$current_branch'. Is this the right branch? [y/N] " answer
[[ "$answer" =~ ^[yYjJ]$ ]] || { echo "Aborted."; exit 1; }

if [[ -n "$(git status --porcelain)" ]]; then
    echo ">>> Changes to be committed:"
    git status --short

    commit_message="${1:-}"
    if [[ -z "$commit_message" ]]; then
        read -r -p "Commit message: " commit_message
    fi
    if [[ -z "$commit_message" ]]; then
        echo "Error: empty commit message. Aborted." >&2
        exit 1
    fi

    read -r -p "Commit ALL changes listed above? [y/N] " answer
    [[ "$answer" =~ ^[yYjJ]$ ]] || { echo "Aborted."; exit 1; }

    git add -A
    git commit -m "$commit_message"
else
    echo ">>> Nothing to commit, pushing existing commits only."
fi

echo ">>> Pushing '$current_branch' to GitHub"
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    git push
else
    git push -u origin "$current_branch"
fi

echo "Done."
