#!/bin/bash

# InvisID AGGRESSIVE System Reset Script
echo "🧹 Performing Hard Wipe of InvisID Data..."

# 1. Jump to project root
cd "$(dirname "$0")/.." || exit

# 2. Kill any uvicorn/python server processes
pkill -f "uvicorn"
pkill -f "main.py"
fuser -k 8000/tcp 2>/dev/null

# 3. Find and delete ALL .db files recursively
find . -name "*.db" -delete
find . -name "*.db-journal" -delete
find . -name "*.db-shm" -delete
find . -name "*.db-wal" -delete

# 4. Wipe all storage folders in both root and app
# We use a loop to handle both possible locations
for dir in "." "app"; do
    rm -rf "$dir/storage/uploads/"*
    rm -rf "$dir/storage/results/"*
    rm -rf "$dir/storage/processed/"*
    
    # Recreate structure with gitkeep
    mkdir -p "$dir/storage/uploads" "$dir/storage/results" "$dir/storage/processed"
    touch "$dir/storage/uploads/.gitkeep" "$dir/storage/results/.gitkeep" "$dir/storage/processed/.gitkeep"
done

echo "✨ Hard Wipe Complete. System is now a blank slate."
echo "🚀 Start server: uv run app/main.py"
