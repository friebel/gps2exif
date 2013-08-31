import calendar
import time
from xml.dom import minidom
from gpsdata import GPSPoint


def timeFromRFC3339(txt):
    dtformat = '%Y-%m-%dT%H:%M:%SZ' 
    try:
        return calendar.timegm(time.strptime(txt, dtformat))
    except ValueError:
        raise ValueError('Cannot parse date: {!r} does not match format {!r}'.format(txt, dtformat))


class GPXFile:
    def __init__(self, file):
        self.tracks = {}
        try:
            doc = minidom.parse(file)
            doc.normalize()
        except:
            return

        gpx = doc.documentElement
        for node in gpx.getElementsByTagName('trk'):
            self._parseTrack(node)

    def _parseTrack(self, trk):
        name = trk.getElementsByTagName('name')[0].firstChild.data

        if name in self.tracks:
            track = self.tracks[name]
        else:
            track = []
            self.tracks[name] = track

        for trkseg in trk.getElementsByTagName('trkseg'):
            for trkpt in trkseg.getElementsByTagName('trkpt'):
                lat = float(trkpt.getAttribute('lat'))
                lon = float(trkpt.getAttribute('lon'))
                ele = float(trkpt.getElementsByTagName('ele')[0].firstChild.data)
                rfc3339 = trkpt.getElementsByTagName('time')[0].firstChild.data
                ptime = timeFromRFC3339(rfc3339)
                track.append(GPSPoint(lat=lat, lon=lon, ele=ele, time=ptime))

        track.sort(key=lambda x: x.time)

    def flatten(self):
        flat = []
        for track, points in self.tracks.iteritems():
            flat.extend(points)
        flat.sort(key=lambda x: x.time)
        self.tracks['flat'] = flat

    def getTrackNames(self):
        return self.tracks.keys()

    def __getitem__(self, key):
        return self.tracks[key]


# vim: set ts=4 sts=4 sw=4
