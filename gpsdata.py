from __future__ import annotations

import math
import re

from typing import Optional
from typing import Type


EARTH_RADIUS = 6378.0


class GPSPoint:
    def __init__(
        self: GPSPoint,
        lat: float,
        lon: float,
        ele: Optional[float] = None,
        time: Optional[float] = None,
    ) -> None:
        if abs(lat) > 180:
            raise ValueError("Invalid latitude")
        if abs(lon) > 90:
            raise ValueError("Invalid longitude")
        self.lat = lat
        self.lon = lon
        self.ele = ele
        self.time = time

    def __repr__(self: GPSPoint) -> str:
        return "GPSPoint({})".format(
            ", ".join(
                (
                    "time={}".format(self.time),
                    "lat={:.6f}".format(self.lat),
                    "lon={:.6f}".format(self.lon),
                    "ele={}".format(self.ele),
                )
            )
        )

    def __str__(self: GPSPoint) -> str:
        s = "<{lat:+.6f},{lon:+.6f}".format(**self.__dict__)
        if self.ele is not None:
            s += ",{ele:.2f}".format(ele=self.ele)
        s += ">"
        return s

    @classmethod
    def from_str(cls: Type[GPSPoint], s: str) -> GPSPoint:
        """
        Create GPSPoint from formatted string.
        :param s: string to interpret, e,g. "<+20.01234,+20.56789>
        :returns: object of class GPSPoint corresponding to the input string
        :raises ValueError: invalid input
        """

        m = re.match(r"<(.*)>", s)
        if m:
            s = m.group(1)
        d = s.split(",")
        if len(d) not in (2, 3):
            raise ValueError("Cannot parse GPSPoint string representation")
        lat = float(d.pop(0))
        lon = float(d.pop(0))
        ele = float(d.pop(0)) if d else None
        return cls(lat, lon, ele)

    def distance(self: GPSPoint, other: GPSPoint) -> float:
        """
        Calculate distance between this and another GPSPoint.
        :param other: other GPSPoint
        :returns: distance in km
        """

        lat1 = self.lat / 180.0 * math.pi
        lon1 = self.lon / 180.0 * math.pi
        lat2 = other.lat / 180.0 * math.pi
        lon2 = other.lon / 180.0 * math.pi

        R = EARTH_RADIUS

        d = R * math.acos(
            math.sin(lat1) * math.sin(lat2)
            + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        )

        return d

    def __sub__(self: GPSPoint, other: GPSPoint) -> float:
        return self.distance(other)

    def interpolate(self: GPSPoint, other: GPSPoint, time: float) -> GPSPoint:
        """Interpolate between two GPSpoints.
        :param other: a second object of class GPSPoint
        :param time: point in time to interpolate; must be between time of this
                     and `other` GPSPoint
        :returns: object of class GPSPoint corresponding to the interpolated
                  location at given `time`
        """

        if self.time is None:
            raise ValueError("GPSPoint must have a time set to interpolate")
        if other.time is None:
            raise ValueError("'other' GPSPoint must have a time set to interpolate")

        if self.time < other.time:
            gps1 = self
            gps2 = other
        else:
            gps1 = other
            gps2 = self

        assert gps1.time is not None
        assert gps2.time is not None
        assert gps1.time <= time and time <= gps2.time

        lat1 = gps1.lat / 180.0 * math.pi
        lon1 = gps1.lon / 180.0 * math.pi
        lat2 = gps2.lat / 180.0 * math.pi
        lon2 = gps2.lon / 180.0 * math.pi

        R = EARTH_RADIUS

        # Calculate current point as fraction between the two GPS points
        frac = (time - gps1.time) / (gps2.time - gps1.time)

        # Calculate distance between start point and interpolated point
        full_dist = gps1.distance(gps2)
        dist = full_dist * frac

        # Calculate initial bearing
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
            lat2
        ) * math.cos(lon2 - lon1)
        brng = math.atan2(y, x)

        # Calculate interpolated point
        lat_i = math.asin(
            math.sin(lat1) * math.cos(dist / R)
            + math.cos(lat1) * math.sin(dist / R) * math.cos(brng)
        )
        lon_i = lon1 + math.atan2(
            math.sin(brng) * math.sin(dist / R) * math.cos(lat1),
            math.cos(dist / R) - math.sin(lat1) * math.sin(lat_i),
        )

        # print("Fraction: {}".format(frac))
        # print("Distance: {}".format(dist))
        # print("Start point:        lat {:.11f} lon {:.11f}".format(lat1, lon1))
        # print("End point:          lat {:.11f} lon {:.11f}".format(lat2, lon2))
        # print("Interpolated point: lat {:.11f} lon {:.11f}".format(lat_i, lon_i))

        new_lat = lat_i / math.pi * 180
        new_lon = lon_i / math.pi * 180
        new_time = time

        if gps1.ele is not None and gps2.ele is not None:
            new_ele = gps1.ele + frac * (gps2.ele - gps1.ele)
            return GPSPoint(lat=new_lat, lon=new_lon, ele=new_ele, time=new_time)

        return GPSPoint(lat=new_lat, lon=new_lon, time=new_time)


# vim: set ts=4 sts=4 sw=4
