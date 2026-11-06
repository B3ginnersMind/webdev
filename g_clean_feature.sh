#!/usr/bin/env bash
# Delete a merged feature branch locally and on GitHub.
# Usage: g_clean_feature.sh [branch-name]
#   Without an argument the current branch is used. After g_ff_merge_feature.sh
#   or g_merge_feature.sh you are on main, so pass the feature branch name.
set -euo pipefail

main_branch="main"

git rev-parse --is-inside-work-tree >/dev/null
feature_branch="${1:-$(git branch --show-current)}"

if [[ -z "$feature_branch" ]]; then
    echo "Error: not on a branch (detached HEAD) and no branch name given." >&2
    exit 1
fi
if [[ "$feature_branch" == "$main_branch" ]]; then
    echo "Error: refusing to delete '$main_branch'." >&2
    echo "Usage: $(basename "$0") <feature-branch>" >&2
    exit 1
fi
if ! git show-ref --verify --quiet "refs/heads/$feature_branch"; then
    echo "Error: local branch '$feature_branch' does not exist." >&2
    exit 1
fi

read -r -p "Delete feature branch '$feature_branch' locally and on GitHub? [y/N] " answer
[[ "$answer" =~ ^[yYjJ]$ ]] || { echo "Aborted."; exit 1; }

if [[ "$(git branch --show-current)" == "$feature_branch" ]]; then
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "Error: working tree has uncommitted changes." >&2
        git status --short
        exit 1
    fi
fi

echo ">>> Updating '$main_branch' from GitHub"
git switch "$main_branch"
git pull --ff-only

# 'git branch -d' refuses to delete a branch that is not merged into main.
echo ">>> Deleting local branch '$feature_branch'"
if ! git branch -d "$feature_branch"; then
    echo "Error: '$feature_branch' is not merged into '$main_branch'. Nothing deleted." >&2
    exit 1
fi

if git ls-remote --exit-code --heads origin "$feature_branch" >/dev/null 2>&1; then
    echo ">>> Deleting '$feature_branch' on GitHub"
    git push origin --delete "$feature_branch"
else
    echo ">>> '$feature_branch' does not exist on GitHub, nothing to delete there."
fi

echo "Done. You are now on '$main_branch'."
