#!/bin/sh

basePath="/Applications/AudioSculpt"
appName=$(ls "$basePath" | grep "AudioSculpt.*\.app")
linkPath="/Applications/AudioSculpt.app"

if [ -L "$linkPath" ]; then
  rm "$linkPath"
fi

ln -s "$basePath/$appName" "$linkPath"

exit 0
