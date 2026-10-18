#!/bin/sh
# Keep Node/npm and all npm children on the pinned project-local runtime.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ ! -x "$repo_root/tools/node/bin/node" ]; then
    echo "Missing project Node runtime; run make bootstrap-tools" >&2
    exit 1
fi
PATH="$repo_root/tools/node/bin:$PATH"
export PATH
exec "$repo_root/tools/node/bin/node" \
    "$repo_root/tools/node/lib/node_modules/npm/bin/npm-cli.js" "$@"
