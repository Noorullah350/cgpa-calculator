#!/data/data/com.termux/files/usr/bin/bash

URL="$1"

if [ -z "$URL" ]; then
    echo "URL is required"
    exit 1
fi

yt-dlp \
    --no-playlist \
    -f "bv*+ba/b" \
    --merge-output-format mp4 \
    -o "/sdcard/Download/VideoFlow_%(title)s.%(ext)s" \
    "$URL"
