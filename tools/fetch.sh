#!/bin/bash
# usage: fetch.sh JOBDIR  (stdin: "relpath url" per line)
J="$1"; cd "$J" || exit 1
while read -r f u; do [ -z "$f" ] && continue; mkdir -p "$(dirname "$f")"; curl -sS --retry 3 -o "$f" "$u" && echo "saved $f $(stat -c %s "$f")" & done; wait
