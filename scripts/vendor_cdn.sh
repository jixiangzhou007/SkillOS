#!/bin/bash
# Download CDN dependencies locally for offline/fallback use
# Run: bash scripts/vendor_cdn.sh
cd "$(dirname "$0")/../frontend"
echo "Downloading CDN dependencies..."
curl -sL -o alpine.min.js "https://cdn.jsdelivr.net/npm/alpinejs@3.14.x/dist/cdn.min.js" && echo "  alpine.min.js OK" || echo "  alpine.min.js FAILED"
curl -sL -o marked.min.js "https://cdn.jsdelivr.net/npm/marked@11/marked.min.js" && echo "  marked.min.js OK" || echo "  marked.min.js FAILED"
echo "Done. Add alpine.min.js and marked.min.js to .gitignore if desired."
