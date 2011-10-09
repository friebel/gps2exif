import sys, string, time, calendar
from xml.dom import minidom, Node

def timeFromRFC3339(txt):
    if txt[-1] == 'Z':
        return calendar.timegm(time.strptime(txt, '%Y-%m-%dT%H:%M:%SZ'))
    else:
        raise RuntimeError('Cannot parse date %s' % repr(txt))

class GPXPoint:
    def __init__(self, time, lat, lon, ele):
        self.time = time
        self.lat = lat
        self.lon = lon
        self.ele = ele

    def __repr__(self):
        return "GPXPoint(%s)" % ', '.join((
            'time=%s' % self.time,
            'lat=%.6f' % self.lat,
            'lon=%.6f' % self.lon,
            'ele=%.3f' % self.ele,
            ))

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
                track.append(GPXPoint(time=ptime, lat=lat, lon=lon, ele=ele))

        track.sort(key=lambda x:x.time)

    def flatten(self):
        flat = []
        for track, points in self.tracks.iteritems():
            flat.extend(points)
        flat.sort(key=lambda x:x.time)
        self.tracks['flat'] = flat

    def getTrackNames(self):
        return self.tracks.keys()

    def __getitem__(self, key):
        return self.tracks[key]


# vim: set ts=4 sts=4 sw=4
