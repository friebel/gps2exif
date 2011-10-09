#!/usr/bin/env python
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

import argparse
import calendar
import gpxparser
import sys
import time
import subprocess


"""Interpret given EXIF time as UTC time.  Timezone adaption should be applied
afterwards."""
def parse_exif_time(txt):
    return time.mktime(time.strptime(txt, "%Y:%m:%d %H:%M:%S"))


"""Parse time (and date) given on command line.  Returning tuple with two elements.
First element is boolean indicating whether a date was given additional to time.
Second alement is the parsed time/date value."""
def parse_cmdline_time(txt):
    # Parse date and time, with date using "-" as separator and time using ":"
    try:
        return (True, time.mktime(time.strptime(txt, "%Y-%m-%d %H:%M:%S")))
    except ValueError:
        pass

    # Parse date and time, with date and time both using ":" as separator
    try:
        return (True, time.mktime(time.strptime(txt, "%Y:%m:%d %H:%M:%S")))
    except ValueError:
        pass

    # Parse time only, with ":" as separator
    try:
        t = time.strptime(txt, "%H:%M:%S")
        t = (2000, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                t.tm_wday, t.tm_yday, t.tm_isdst)
        return (False, time.mktime(t))
    except ValueError:
        pass

def format_time_delta(delta):
    if not delta:
        return ""

    neg = (delta < 0)
    delta = abs(int(delta))

    if neg:
        sign = "-"
    else:
        sign = "+"

    return "%s%d:%02d:%02d" % (
            sign,
            delta / 3600,
            delta / 60 % 60,
            delta % 60,
        )


def process_timeref_args(ref_image, ref_time):
    global args

    (ref_time_hasdate, ref_time) = parse_cmdline_time(ref_time)

    # Read time from reference image
    try:
        ref_img_timestr = subprocess.check_output(
                ["exif", "-mt", "0x9003", ref_image.name])
        ref_img_time = parse_exif_time(ref_img_timestr.strip())
    except subprocess.CalledProcessError:
        print "Error: Could not execute 'exif'"
        return 1

    # Set reference date of file when no date given
    if not ref_time_hasdate:
        img = time.localtime(ref_img_time)
        ref = time.localtime(ref_time)
        ref_time = time.mktime((
            img.tm_year, img.tm_mon, img.tm_mday,
            ref.tm_hour, ref.tm_min, ref.tm_sec,
            img.tm_wday, img.tm_yday, img.tm_isdst))

    # Calculate time offset
    time_offset = ref_time - ref_img_time

    # Print some info
    if args.verbosity >= 1:
        print "Reference image date/time is set to: %s" % \
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ref_img_time))
        print "Reference image date/time should be: %s" % \
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ref_time))
        print "Date/time fixing delta: %s" % \
                format_time_delta(time_offset)

    return time_offset


def main():
    global args

    description="Set image location EXIF tags from corrsponding GPS track." \
            " Optionally fix the images' date/time offset first."
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--ref-img", dest="ref_image", type=file,
            help="reference image file name for fixing time offset using --ref-time")

    parser.add_argument("--ref-time", dest="ref_time",
            help=
            "Corrected reference image date/time to calculate time offset."
            " If one of --ref-img and --ref-time is given the other one must be given too.")

    parser.add_argument("--fix-time", dest="fix_time",
            help=
            "Apply given time offset to all images."
            " Example: '--fix-time +1:09' to add 1 minute, 9 seconds"
            " to the images' EXIF time.")

    parser.add_argument("--gpx", dest="gpx", metavar="GPX", type=file, action="append",
            help=".gpx GPS track file")

    parser.add_argument("-n", dest="no_action", action="store_true", default=False,
            help=".gpx GPS track file")

    parser.add_argument("-v", dest="verbosity", action="count", default=0,
            help=".gpx GPS track file")

    parser.add_argument("images", metavar="IMAGE", type=file, nargs="+",
            help="image file to process")

    try:
        args = parser.parse_args()
    except IOError, e:
        print e
        return 1

    #print args

    # ref_image and ref_time must be given both or none
    if bool(args.ref_image) ^ bool(args.ref_time):
        parser.error("Options --ref-img and --ref-time must be given both or none.")

    # check that we can execute "exif"
    try:
        subprocess.check_output(["exif", "-v"])
    except subprocess.CalledProcessError:
        print "Error: Could not execute 'exif' application"
        return 1

    # Time zone info
    if args.verbosity >= 1:
        print "Assuming image time zone %s/%s" % time.tzname

    # Calculate time offset to apply
    if args.ref_image or args.ref_time:
        time_offset = process_timeref_args(args.ref_image, args.ref_time)
    else:
        time_offset = None

    # Read GPS data
    gpx = []
    for gpxfile in args.gpx:
        print "Reading GPX file %s" % gpxfile.name
        data = gpxparser.GPXFile(gpxfile)
        data.flatten()
        gpx.append(data)

        if args.verbosity >= 2:
            for p in data["flat"]:
                print p

    # Fix time offset
    if time_offset:
        print "Applying date/time delta %s" % \
                format_time_delta(time_offset)

        for target in args.images:
            print "  processing %s" % target.name

            #exif -m -t 0x9003 TIMESRC.JPG
            #  Fetch Date and Time (Original)
            #  Output: "2011:08:14 19:42:33"
            #exif -m -t 0x9291 TIMESRC.JPG
            #  Fetch original subsecond
            #  Output: "20"

    # Set GPS data
    if gpx:
        print "Setting GPS data"

        for target in args.images:
            print "  processing %s" % target.name


if __name__ == "__main__":
    res = main()
    sys.exit(res)


# vim: set ts=4 sts=4 sw=4
