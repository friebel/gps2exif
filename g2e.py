# Using Exiv2:
#   exiv2 -T mv DST.JPG
#     Set date/time from timestampt
#   exiv2 -a '-0:00:30' ad DST.JPG
#     Shift exif timestamp
#     Removes SubSecTime[Original|Digitized]
#   exiv2 fixiso DST.JPG
#     Create exif ISO entry from Nikon entry
# Using exif:
#   exif -m -t 0x9003 TIMESRC.JPG
#     Fetch Date and Time (Original)
#     Output: "2011:08:14 19:42:33"
#   exif -m -t 0x9291 TIMESRC.JPG
#     Fetch original subsecond
#     Output: "20"
# Notes:
# * Image time zone as cmd line parameter

import time

"""Interpret given EXIF time as UTC time.  Timezone adaption should be applied
afterwards."""
def exifTimeParser(txt):
    return calendar.timegm(time.strptime(txt, '%Y:%m:%d %H:%M:%S'))


# vim: set ts=4 sts=4 sw=4
