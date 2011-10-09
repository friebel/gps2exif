#!/usr/bin/env python
# Using Exiv2:
#   exiv2 -T mv DST.JPG
#     Set date/time from timestamp
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


def format_exif_time(secs):
    return time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(secs))


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

    raise ValueError("Can not parse date/time %s" % repr(txt))


def format_time_offset(delta):
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


def parse_time_offset(txt):
    parse_err = ValueError("Can not parse time offset %s" % repr(txt))

    if not txt:
        raise parse_err

    # Save and remove +/- sign
    if txt[0] == '+':
        sign = 1
    elif txt[0] == '-':
        sign = -1
    else:
        raise parse_err

    txt = txt[1:]

    # Parse days
    values = txt.split(' ', 1)
    if len(values) > 1:
        try:
            days = int(values[0])
        except ValueError:
            raise parse_err
        txt = values[1]
    else:
        days = 0

    # Parse [[%H:]%M:]%S
    values = txt.split(':', 2)

    secs = int(values[-1])
    del values[-1]

    if values:
        mins = int(values[-1])
        del values[-1]
    else:
        mins = 0

    if values:
        hours = int(values[-1])
        del values[-1]
    else:
        hours = 0

    offset = ((days * 24 + hours) * 60 + mins) * 60 + secs

    return sign * offset


def exif_get_time(filename):
    img_time = subprocess.check_output(
            ["exif", "-mt", "0x9003", filename])
    img_time = parse_exif_time(img_time.strip())

    return img_time


def exif_set_time(filename, time_val):
    time_str = format_exif_time(time_val)
    subprocess.check_output(
            ["exif", "--ifd=EXIF", "-mt", "0x9003", "--set-value", time_str, "-o", filename, filename])


def process_timeref_args(ref_image, ref_time):
    global args

    (ref_time_hasdate, ref_time) = parse_cmdline_time(ref_time)

    # Read time from reference image
    ref_img_time = exif_get_time(ref_image.name)

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
        print "Reference image date/time is set to: %s.%02d" % (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ref_img_time)),
                (ref_img_time % 1) * 100,
            )
        print "Reference image date/time should be: %s.%02d" % (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ref_time)),
                (ref_time % 1) * 100,
            )
        print "Date/time fixing delta: %s" % \
                format_time_offset(time_offset)

    return time_offset


def gpx_find_enclosing(gpxs, file_time):
    # TODO: timezone conversion necessary?

    for gpx in gpxs:
        # Skip gpx if file time is out of its bounds
        if file_time < gpx["flat"][0].time:
            return None
        if file_time > gpx["flat"][-1].time:
            return None

        for idx, p in enumerate(gpx["flat"][1:]):
            if file_time < p.time:
                return (gpx["flat"][idx], p)

    return None


def main():
    global args

    description="Set image location EXIF tags from corrsponding GPS track." \
            " Optionally shift the images' date/time first."
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--ref-img", dest="ref_image", type=file,
            help="reference image file name for shifting time using --ref-time")

    parser.add_argument("--ref-time", dest="ref_time",
            help=
            "Corrected reference image date/time to calculate time offset for shifting."
            " If one of --ref-img and --ref-time is given the other one must be given too.")

    parser.add_argument("--shift-time", dest="shift_time",
            help=
            "Shift time of all images by given offset."
            " Example: '--shift-time=+1:09' to add 1 minute, 9 seconds"
            " to the images' EXIF time.")

    parser.add_argument("--gpx", dest="gpxs", metavar="GPX", type=file, action="append", default=[],
            help=".gpx GPS track file")

    parser.add_argument("-n", dest="no_action", action="store_true", default=False,
            help="do not change any files")

    parser.add_argument("-v", dest="verbosity", action="count", default=0,
            help="increase verbosity")

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

    if bool(args.ref_image) and args.shift_time:
        parser.error("Option --shift-time can not be used with --ref-img/--ref-time.")

    # check that we can execute "exif"
    try:
        subprocess.check_output(["exif", "-v"])
    except subprocess.CalledProcessError:
        print "Error: Could not execute 'exif' application"
        return 1

    # Time zone info
    if args.verbosity >= 1:
        print "Assuming image time zone %s/%s" % time.tzname

    time_offset = None

    # Parse time offset given at command line
    if args.shift_time:
        time_offset = parse_time_offset(args.shift_time)

    # Calculate time offset from reference image
    if args.ref_image or args.ref_time:
        try:
            time_offset = process_timeref_args(args.ref_image, args.ref_time)
        except subprocess.CalledProcessError:
            print "Error executing exif"
            return -1

    # Read GPS data
    gpxs = []
    for gpxfile in args.gpxs:
        print "Reading GPX file %s" % gpxfile.name
        data = gpxparser.GPXFile(gpxfile)
        data.flatten()
        gpxs.append(data)

        if args.verbosity >= 2:
            for p in data["flat"]:
                print p

    # Fix time offset
    if time_offset:
        print "Applying date/time delta %s" % \
                format_time_offset(time_offset)

        for target in args.images:
            print "  %s" % target.name

            file_time = exif_get_time(target.name)
            new_time = file_time + time_offset

            if args.no_action:
                continue

            exif_set_time(target.name, new_time)

    # Set GPS data
    if gpxs:
        print "Setting GPS data"

        for target in args.images:
            print "  %s" % target.name

            file_time = exif_get_time(target.name)
            gpx_points = gpx_find_enclosing(gpxs, file_time)
            # TODO


if __name__ == "__main__":
    res = main()
    sys.exit(res)


# vim: set ts=4 sts=4 sw=4
