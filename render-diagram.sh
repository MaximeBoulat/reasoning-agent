#!/usr/bin/env bash
# Usage: ./render-diagram.sh path/to/answer.md [output.svg]
set -euo pipefail

INPUT="${1:?usage: render-diagram.sh <file.md> [output.svg]}"
OUTPUT="${2:-${INPUT%.*}.png}"
MMD="$(mktemp -t diagram).mmd"

# Extract the first ```mermaid ... ``` fenced block
awk '/^```mermaid/{flag=1; next} /^```/{if(flag){flag=0}} flag' "$INPUT" > "$MMD"

if [ ! -s "$MMD" ]; then
    echo "No \`\`\`mermaid block found in $INPUT" >&2
    exit 1
fi

npx -y @mermaid-js/mermaid-cli -i "$MMD" -o "$OUTPUT" --size 4000 -s 3 -b white

echo "Rendered: $OUTPUT"
echo "Source extracted to: $MMD"
