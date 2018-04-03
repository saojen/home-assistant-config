"""
Adds sensor to HA with DuneHD media player current activity.
Arguments:
 - host			- hostname or IP address of the DuneHD media player (required)
 - interval		- interval scanning, default 60 sec. (optional)

Configuration example:

dune_activity:
  module: dune_activity
  class: DuneActivity
  host: !secret brother_hostname
  status_interval: 5

"""

import appdaemon.plugins.hass.hassapi as hass
import requests
from datetime import datetime
import re

class DuneActivity(hass.Hass):

    def initialize(self):

        __version__ = '0.1.2'

        self.URL_FORMAT = "http://{}/cgi-bin/do"

        try:
            if self.args['host']:
                self.host = self.args['host']
        except KeyError:
            self.error("Wrong arguments! You must supply a valid DuneHD " \
                       "media player hostname or IP address.")
            return
        try:
            if 'interval' in self.args:
                interval = int(self.args['interval'])
            else:
                interval = 60
        except ValueError:
            self.error("Wrong arguments! Argument interval has to be an " \
                       "integer.")
            return
        self.run_every(self.update_activity, datetime.now(), interval)

    def update_activity(self, kwargs):
        request = None
        try:
            request = requests.get(self.URL_FORMAT.format(self.host), \
                                   timeout = 2)
        except requests.exceptions.RequestException:
            pass
        if not request:
            state = 'offline'
        elif request.status_code == 200:
            pattern = re.compile(".*name=\"player_state\" value=\"(.*)\"")
            state = findall(pattern, request.text)[0]
        else:
            state = 'offline'
        try:
            self.set_state('sensor.dune_activity', state = state)
        except:
            return
