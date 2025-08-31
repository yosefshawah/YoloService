#!/bin/bash

echo "🧹 Starting macOS cleanup..."

# 1️⃣ Remove user caches
echo "Clearing user caches..."
rm -rf ~/Library/Caches/* 2>/dev/null

# 2️⃣ Remove system logs and temporary files
echo "Clearing system logs and temp files..."
sudo rm -rf /Library/Logs/* /private/var/log/* /private/var/tmp/* /tmp/* 2>/dev/null

# 3️⃣ Remove old Time Machine local snapshots
echo "Removing Time Machine local snapshots..."
sudo tmutil listlocalsnapshots / | awk -F. '{print $4}' | while read snap; do
    sudo tmutil deletelocalsnapshots $snap
done

# 4️⃣ Remove old iOS backups
echo "Checking for old iOS backups..."
if [ -d ~/Library/Application\ Support/MobileSync/Backup/ ]; then
    echo "Old iOS backups folder exists. You can review and delete manually if needed:"
    open ~/Library/Application\ Support/MobileSync/Backup/
fi

# 5️⃣ Clean Docker
echo "Pruning Docker system (images, containers, volumes)..."
docker system prune -af --volumes 2>/dev/null

# 6️⃣ Optional: Clear Xcode derived data and simulators
if [ -d ~/Library/Developer/Xcode ]; then
    echo "Cleaning Xcode DerivedData..."
    rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null
    echo "Deleting unavailable simulators..."
    xcrun simctl delete unavailable 2>/dev/null
fi

echo "✅ Cleanup finished! Please restart your Mac for changes to reflect in System Data."

