### AutoPkg for Ircam Forum software

#### Custom Processor

A combination of URLDownloader and URLTextSearcher, which authenticates with the Forum login page and creates a persistent Cookie Jar file that it passed between the various URL processes. This will likely be superseded by a more streamlined processor when the new URLDownloader and URLTextSearcher processors are released with extended curl option parsing.

#### Suggested Munki pre/post install scripts

The following scripts are included in the input section of the Munki Recipe, although can be overridden if desired.

##### preinstall_script

The installer will not overwrite the AudioSculpt directory, which can lead to some duplication of content. A solution is to remove before commencing the install:

```
#!/bin/sh

audiosculptPath="/Applications/AudioSculpt"

# Clear AS path before installing
if [ -d "$audiosculptPath" ]; then
  rm -r "$audiosculptPath"
fi

exit 0
```

##### postinstall_script

The AudioSculpt application is renamed on each release to `AudioSculpt %version%.app`, which is problematic for links, static Dock etc. The application can't be renamed during the AutoPkg process as the folder hierarchy has various embedded symlinks that refer to the application path by name. A solution therefore is to run a  script that creates a symlink to the Audiosculpt applications, e.g:

```
#!/bin/sh

basePath="/Applications/AudioSculpt"
appName=$(ls "$basePath" | grep "AudioSculpt.*\.app")
linkPath="/Applications/AudioSculpt.app"

if [ -L "$linkPath" ]; then
  rm "$linkPath"
fi

ln -s "$basePath/$appName" "$linkPath"

exit 0
```
