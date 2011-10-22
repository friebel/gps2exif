gps2exif - GPS-tagging of JPEG files
====================================
gps2exif reads .gpx files and tags JPEG images according to the time they have
been taken.  It allows to fix image date/time and interpolates between GPS
points.

General syntax
--------------
 gps2exif [-h] [-n] [-v] [--gpx GPX]
 [--ref-img REF_IMAGE] [--ref-time REF_TIME]
 [--shift-time SHIFT_TIME] [--max-dist MTRS] [--max-span SECS]
 [--ok-dist MTRS] [--ok-span SECS] IMAGE [IMAGE ...]

You can give multiple .gpx files using the '--gpx FILE' switch multiple times.
Give the names of the image files to be processed at the end of the command
line.  The switch '-n' will make a dry-run and not change any file.  The '-v'
switch increases verbosity.

Fixing image date/time
----------------------
A precise date/time stored in the image's EXIF data is crucial for associating
the GPS track with the image.  gps2exif offers two ways to fix the date/time
stored in the JPEG files before looking up the GPS coorinates:

- You can either give the name of a file and the correct date/time of the file.
  gps2exif will calculate the time offset and apply it to all given images.
  This is ideal if you took a photo of your GPS device showing GPS time.

  The syntax is '--ref-img REF_IMAGE --ref-time REF_TIME'.  REF_TIME should be
  formatted like '2011-10-22 14:42:07'.
- If you know the time offset, you can give it via '--shift-time SHIFT_TIME'.
  For example, use '--shift-time=+1:09' to add 1 minute, 9 seconds to the time
  of each image.

Setting thresholds
------------------
Under some circumstances GPS devices do not store enough points to make a
precise-enough guess about the location a photo was taken at.  You can set the
thresholds that control whether the GPS data is deemed good enough or not.

The thresholds are checked on the two GPS points around the time your photo was
taken:  the last GPS point before and the first GPS point after the time of
your photo.  You can set thresholds on the time span and the distance between
these two GPS points.

With '--max-dist MTRS' and '--max-span SECS' you set hard thresholds.  A photo
will not be GPS-tagged if the two enclosing GPS points are more than MTRS
meters or more than SECS seconds apart.

With '--ok-dist MTRS' and '--ok-span SECS' you set the okay criteria.  A photo
will not be GPS-tagged if the two GPS enclosing points are neither closer than
MTRS meter nor closer than SECS seconds.

To GPS-tag a photo always both max criteria and at least one ok criterion must
be met.
