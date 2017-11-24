#!/bin/sh

audiosculptPath="/Applications/AudioSculpt"

# Clear AS path before installing
if [ -d "$audiosculptPath" ]; then
  rm -r "$audiosculptPath"
fi

exit 0
