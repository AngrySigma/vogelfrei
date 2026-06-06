#!/usr/bin/env bash
#
# snapshot-nightly.sh — publish the current site source to the `nightly`
# branch so the in-progress state of the rulebook is visible on GitHub.
#
# Meant to be called by the same daily cron that rebuilds vogelfrei.ru,
# right after the build. It captures a *buildable* snapshot:
#
#   * every tracked file at its current on-disk content (build config:
#     zensical.toml, pyproject.toml, uv.lock, .python-version, etc.)
#   * everything under docs/ — INCLUDING untracked files (new pages,
#     images), so work that hasn't been committed yet still shows up
#   * .gitignore is respected, so /site, .venv, __pycache__ never leak
#
# It deliberately does NOT include untracked scratch outside docs/
# (combat_sim/, tests/, fix_*.py, ...): those aren't part of the site.
#
# The snapshot is built in a throwaway index with plumbing commands, so
# the live checkout is never touched — no checkout, no staged changes,
# no branch switch. The working copy keeps building from whatever branch
# it was on, exactly as before.
#
# Usage:
#   scripts/snapshot-nightly.sh            # build + push to origin/nightly
#   scripts/snapshot-nightly.sh --dry-run  # build + report, do not push
#
# Env:
#   NIGHTLY_REMOTE   git remote to push to (default: origin)
#   NIGHTLY_BRANCH   branch name to publish (default: nightly)
#
set -euo pipefail

REMOTE="${NIGHTLY_REMOTE:-origin}"
BRANCH="${NIGHTLY_BRANCH:-nightly}"
BRANCH_REF="refs/heads/${BRANCH}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

cd "$(git rev-parse --show-toplevel)"

# Build the tree in a temporary index so the real index / working tree
# / HEAD are all left untouched.
TMP_INDEX="$(mktemp)"
export GIT_INDEX_FILE="$TMP_INDEX"
trap 'rm -f "$TMP_INDEX"' EXIT

git read-tree HEAD          # start from the current commit's tracked tree
git add -u                  # fold in worktree edits/deletes to tracked files
git add -- docs             # add untracked docs/ files (respects .gitignore)

TREE="$(git write-tree)"

SRC_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
SRC_SHA="$(git rev-parse --short HEAD)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
MSG="nightly snapshot ${STAMP} — source ${SRC_BRANCH}@${SRC_SHA}"

# Chain onto the previous nightly (if any) so the branch accumulates a
# day-by-day history of how the game evolved. First run creates it.
git fetch -q "$REMOTE" "$BRANCH" 2>/dev/null || true
PARENT="$(git rev-parse -q --verify "${REMOTE}/${BRANCH}" 2>/dev/null || true)"

if [ -n "$PARENT" ] && \
   [ "$(git rev-parse "${PARENT}^{tree}")" = "$TREE" ]; then
    echo "nightly: site source unchanged since last snapshot — nothing to push."
    exit 0
fi

COMMIT="$(git commit-tree "$TREE" ${PARENT:+-p "$PARENT"} -m "$MSG")"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY RUN — would push to ${REMOTE} ${BRANCH_REF}"
    echo "  commit:  $COMMIT"
    echo "  message: $MSG"
    echo "  files:   $(git ls-tree -r --name-only "$TREE" | wc -l) tracked into snapshot"
    echo "  top-level entries:"
    git ls-tree --name-only "$TREE" | sed 's/^/    /'
    exit 0
fi

git push "$REMOTE" "${COMMIT}:${BRANCH_REF}"
echo "nightly: pushed ${COMMIT} -> ${REMOTE}/${BRANCH}"
