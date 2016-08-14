# Using Exiv2:
#   > exiv2 -T mv DST.JPG
#     Set file timestamp from exif data
#
#   > exiv2 -a '-0:00:30' ad DST.JPG
#     Shift exif timestamp
#     Removes SubSecTime[Original|Digitized]
#
#   > exiv2 fixiso DST.JPG
#     Create exif standard ISO entry from Nikon entry
#
#   > exiv2 -Pv -g "Exif.Image.DateTime" pr DST.JPG
#   < 2011:08:14 19:42:33
#
#   > exiv2 -Pv -g "Exif.GPSInfo.GPSVersionID" pr GPS_EXAMPLE.JPG
#   < 2 2 0 0
#
#   > exiv2 -Pkv pr GPS_EXAMPLE.JPG | grep GPS
#   < Exif.Image.GPSTag                             2634
#   < Exif.GPSInfo.GPSVersionID                     2 2 0 0
#   < Exif.GPSInfo.GPSLatitudeRef                   N
#   < Exif.GPSInfo.GPSLatitude                      51/1 1/1 10137/625
#   < Exif.GPSInfo.GPSLongitudeRef                  E
#   < Exif.GPSInfo.GPSLongitude                     13/1 52/1 12999/250
#   < Exif.GPSInfo.GPSMapDatum                      WGS-84

#   < Exif.GPSInfo.GPSAltitude                      501/10
#   < Exif.GPSInfo.GPSAltitudeRef                   0
#
#   > exiv2 -M"set Exif.GPSInfo.GPSLatitude 4/1 15/1 33/1" -M"set Exif.GPSInfo.GPSLatitudeRef N" GPSDST.JPG
#     Set GPS info
#
# Using exif:
# The exif tool does not correctly support GPS data.  The following data points
# are not correctly implemented:
#                   ("GPS", "0x0001", "N"),                 # North or South
#                   ("GPS", "0x0002", "51, 1, 49.273"),     # Latitude
#   exif -m -t 0x9003 TIMESRC.JPG
#     Fetch Date and Time (Original)
#     Output: "2011:08:14 19:42:33"
#   exif -m -t 0x9291 TIMESRC.JPG
#     Fetch original subsecond
#     Output: "20"

import subprocess
import time

LATRES = 625
LONRES = 250
ALTRES = 10

exif = None


def parse_time(txt):
    """Interpret given EXIF time as UTC time.  Timezone adaption should be applied
    afterwards."""
    return time.mktime(time.strptime(txt, "%Y:%m:%d %H:%M:%S"))


def format_time(secs):
    return time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(secs))


def parse_rational(txt):
    comps = txt.split('/')
    if len(comps) != 2:
        raise ValueError("Not a valid rational number: {!r}".format(txt))
    return float(int(comps[0])) / int(comps[1])


def format_rational(num, res=1000):
    return "{:d}/{:d}".format(int(round(num * res)), res)


def parse_latlon(txt):
    dms = txt.split()
    if len(dms) != 3:
        raise ValueError("Not a valid coordinate: {!r}".format(txt))
    dms = [parse_rational(c) for c in dms]
    deg = dms[0] + dms[1] / 60 + dms[2] / 3600
    return deg


def format_latlon(num, sec_res=1000):
    num = abs(num)
    d = int(num)
    num -= d
    num *= 60
    m = int(num)
    num -= m
    num *= 60
    s = num
    return " ".join([format_rational(n, r) for n, r in ((d, 1), (m, 1), (s, sec_res))])


class exif_exif:
    def __init__(self):
        try:
            subprocess.check_output(["exif", "-v"])
        except subprocess.CalledProcessError:
            raise

    def get_time(self, filename):
        img_time = subprocess.check_output(
                ["exif", "-mt", "0x9003", filename]).decode(encoding='UTF-8')
        img_time = parse_time(img_time.strip())
        return img_time

    def set_time(self, filename, time_val):
        time_str = format_time(time_val)
        subprocess.check_output(
                ["exif", "--ifd=EXIF", "-mt", "0x9003", "--set-value", time_str, "-o", filename, filename])


class exif_exiv2:
    #DATETIME_KEY = "Exif.Image.DateTime"
    DATETIME_KEY = "Exif.Photo.DateTimeOriginal"

    def __init__(self):
        try:
            subprocess.check_output(["exiv2", "-V"])
        except subprocess.CalledProcessError:
            raise

    def get(self, filename, key):
        prog = subprocess.Popen(["exiv2", "-Pv", "-g", key, "pr", filename], stdout=subprocess.PIPE)
        prog.wait()
        return prog.stdout.read().decode(encoding='UTF-8').strip()

    def set(self, filename, kvlist):
        assert kvlist
        params = ["-M set {} {}".format(k, v) for k, v in kvlist]
        cmdline = ["exiv2"] + params + [filename]
        prog = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
        prog.wait()

    def get_time(self, filename):
        img_time = self.get(filename, self.DATETIME_KEY)
        img_time = parse_time(img_time)
        return img_time

    def set_time(self, filename, time_val):
        # TODO: preserve subsecond
        time_str = format_time(time_val)
        self.set(filename, ((self.DATETIME_KEY, time_str), ))

    def get_gpslat(self, filename):
        lat = self.get(filename, "Exif.GPSInfo.GPSLatitude")
        try:
            lat = parse_latlon(lat)
        except ValueError:
            return None

        ref = self.get(filename, "Exif.GPSInfo.GPSLatitudeRef")
        if ref not in ["N", "S"]:
            return None

        if ref == "S":
            lat = -lat

        return lat

    def get_gpslon(self, filename):
        lon = self.get(filename, "Exif.GPSInfo.GPSLongitude")
        try:
            lon = parse_latlon(lon)
        except ValueError:
            return None

        ref = self.get(filename, "Exif.GPSInfo.GPSLongitudeRef")
        if ref not in ["E", "W"]:
            return None

        if ref == "W":
            lon = -lon

        return lon

    def get_gpsalt(self, filename):
        alt = self.get(filename, "Exif.GPSInfo.GPSAltitude")
        try:
            alt = parse_rational(alt)
        except ValueError:
            return None

        ref = self.get(filename, "Exif.GPSInfo.GPSAltitudeRef")
        if ref not in ["0", "1"]:
            return None

        if ref == "1":
            # Below sea level
            alt = -alt

        return alt

    def get_gpslocation(self, filename):
        lat = self.get_gpslat(filename)
        lon = self.get_gpslon(filename)
        alt = self.get_gpsalt(filename)

        return (lat, lon, alt)

    def set_gpslocation(self, filename, lat, lon, alt):
        data = []

        if lat != None:
            if lat >= 0:
                data.append(("Exif.GPSInfo.GPSLatitudeRef", "N"))
            else:
                data.append(("Exif.GPSInfo.GPSLatitudeRef", "S"))
            data.append(("Exif.GPSInfo.GPSLatitude", format_latlon(lat, LATRES)))

        if lon != None:
            if lon >= 0:
                data.append(("Exif.GPSInfo.GPSLongitudeRef", "E"))
            else:
                data.append(("Exif.GPSInfo.GPSLongitudeRef", "W"))
            data.append(("Exif.GPSInfo.GPSLongitude", format_latlon(lon, LONRES)))

        if alt != None:
            if alt >= 0:
                data.append(("Exif.GPSInfo.GPSAltitudeRef", "0"))
            else:
                data.append(("Exif.GPSInfo.GPSAltitudeRef", "1"))
            data.append(("Exif.GPSInfo.GPSAltitude", format_rational(alt, ALTRES)))

        if data:
            data.append(("Exif.GPSInfo.GPSVersionID", "2 2 0 0"))
            data.append(("Exif.GPSInfo.GPSMapDatum", "WGS-84"))

        self.set(filename, data)


def init():
    global exif

    try:
        exif = exif_exiv2()
        return exif
    except:
        pass

    try:
        exif = exif_exif()
        return exif
    except:
        pass

    return False


def get_time(filename):
    return exif.get_time(filename)


def set_time(filename, time_val):
    return exif.set_time(filename, time_val)


def get_gpslocation(filename):
    return exif.get_gpslocation(filename)


def set_gpslocation(filename, lat, lon, alt):
    return exif.set_gpslocation(filename, lat, lon, alt)


# vim: set ts=4 sts=4 sw=4
