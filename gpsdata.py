import math

EARTH_RADIUS = 6378.0

class GPSPoint:
    def __init__(self, lat, lon, ele=0, time=0):
        self.lat = lat
        self.lon = lon
        self.ele = ele
        self.time = time

    def __repr__(self):
        return "GPSPoint(%s)" % ', '.join((
            'time=%s' % self.time,
            'lat=%.6f' % self.lat,
            'lon=%.6f' % self.lon,
            'ele=%.3f' % self.ele,
            ))

    """Calculate distance in km between two GPS points."""
    def distance(self, other):
        lat1 = self.lat / 180. * math.pi
        lon1 = self.lon / 180. * math.pi
        lat2 = other.lat / 180. * math.pi
        lon2 = other.lon / 180. * math.pi

        R = EARTH_RADIUS

        d = R * math.acos(
                math.sin(lat1) * math.sin(lat2) + 
                math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
            )

        return d

    """Interpolate between two GPS points."""
    def interpolate(self, other, time):
        if self.time < other.time:
            gps1 = self
            gps2 = other
        else:
            gps1 = other
            gps2 = self

        assert gps1.time <= time and time <= gps2.time

        lat1 = gps1.lat / 180. * math.pi
        lon1 = gps1.lon / 180. * math.pi
        lat2 = gps2.lat / 180. * math.pi
        lon2 = gps2.lon / 180. * math.pi


        R = EARTH_RADIUS

        # Calculate current point as fraction between the two GPS points
        frac = (time - gps1.time) / (gps2.time - gps1.time)

        # Calculate distance between start point and interpolated point
        full_dist = gps1.distance(gps2)
        dist = full_dist * frac

        # Calculate initial bearing
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - \
            math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        brng = math.atan2(y, x)

        # Calculate interpolated point
        lat_i = math.asin(
                math.sin(lat1) * math.cos(dist / R) + \
                math.cos(lat1) * math.sin(dist / R) * math.cos(brng)
            )
        lon_i = lon1 + math.atan2(
                math.sin(brng) * math.sin(dist / R) * math.cos(lat1), 
                math.cos(dist / R) - math.sin(lat1) * math.sin(lat_i)
            )

        #print "Fraction: %s" % frac
        #print "Distance: %s" % dist
        #print "Start point:        lat %.11f lon %.11f" % (lat1, lon1)
        #print "End point:          lat %.11f lon %.11f" % (lat2, lon2)
        #print "Interpolated point: lat %.11f lon %.11f" % (lat_i, lon_i)

        data = {
                'lat' : lat_i / math.pi * 180,
                'lon' : lon_i / math.pi * 180,
                'ele' : gps1.ele + frac * (gps2.ele - gps1.ele),
                'time' : time,
            }

        return GPSPoint(**data)


# vim: set ts=4 sts=4 sw=4
