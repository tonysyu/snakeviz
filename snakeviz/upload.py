"""
This module contains the handlers for the upload page and the JSON
request URL. In the standalone, command line version the upload handler
is not used.

"""

import pstats
import json
import tempfile
import os
import multiprocessing as mp

from tornado import ioloop
from tornado.web import asynchronous

from . import handler


def storage_name(filename):
    """
    Prepend the temporary file directory to the input `filename`.

    Parameters
    ----------
    filename : str
        Any name to give a file.

    Returns
    -------
    tempname : str
        `filename` with temporary file directory prepended.

    """
    if len(filename) == 0:
        raise ValueError('filename must have length greater than 0.')

    return os.path.join(tempfile.gettempdir(), filename)


class UploadHandler(handler.Handler):
    """
    Handler for a profile upload page. Not used in the command line
    version.

    """
    def get(self):
        self.render('upload.html')

    def post(self):
        filename = self.request.files['profile'][0]['filename']
        sfilename = storage_name(filename)

        # save the stats info to a file so it can be loaded by pstats
        with open(sfilename, 'wb') as f:
            f.write(self.request.files['profile'][0]['body'])

        # test whether this can be opened with pstats
        try:
            pstats.Stats(sfilename)

        except:
            os.remove(sfilename)
            error = 'There was an error parsing {0} with pstats.'
            error = error.format(filename)
            self.render('upload.html', error=error)

        else:
            self.redirect('viz/' + filename)


# JSON doesn't like sequences as keys and the stats dict has tuples of
# (file name, line number, function name) as keys.
# This custom encoder converts all the keys the stats dict from tuples to
# CSV strings.
class StatsEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, dict):
            nd = {}
            for k, v in obj.iteritems():
                nk = ','.join(str(s) for s in k)
                nv = list(v)
                nv[4] = {}
                for subk, subv in v[4].iteritems():
                    nv[4][','.join(str(s) for s in subk)] = subv
                nd[nk] = tuple(nv)
            obj = nd
        return super(StatsEncoder, self).encode(obj)


def stats_to_json(filename):
    """
    Return the pstats.Stats.stats dictionary from input stats file as JSON.

    """
    stats = pstats.Stats(filename).stats
    return json.dumps(stats, cls=StatsEncoder)


class StatsHandler(handler.Handler):
    """
    Handler for requesting the JSON representation of a profile.
    """

    _timer = None
    _pool = None
    _timeout = None
    _result = None

    @asynchronous
    def get(self, prof_name):
        if self.request.path.startswith('/json/file/'):
            if self.settings['single_user_mode']:
                if prof_name[0] != '/':
                    prof_name = '/' + prof_name
                filename = os.path.abspath(prof_name)
            else:
                self.send_error(status_code=404)
        else:
            filename = storage_name(prof_name)

        self._pool = mp.Pool(1, maxtasksperchild=1)
        self._result = self._pool.apply_async(stats_to_json, (filename,))

        # TODO: Make the timeout parameters configurable
        self._timeout = 10  # in seconds
        self._period = 0.1  # in seconds
        self._timer = ioloop.PeriodicCallback(self._result_callback,
                                              self._period * 1000,
                                              ioloop.IOLoop.instance())
        self._timer.start()

    def _result_callback(self):
        try:
            content = self._result.get(0)
            self._finish_request(content)
        except mp.TimeoutError:
            self._timeout -= self._period
            if self._timeout < 0:
                self._finish_request('')

    def _finish_request(self, content):
        self._timer.stop()
        self._pool.terminate()
        self._pool.close()
        if content:
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(content)
        self.finish()
