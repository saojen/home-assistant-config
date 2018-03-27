"""
Adds four sensors to HA with data from brother network printer WWW interface. Tested only with Brother HL-L2340DW.
Arguments:
 - host					- hostname or IP address of the printer (required)
 - status_interval		- interval scanning for status page, default 10 sec. [status and remain toner sensors] (optional)
 - info_interval		- interval scanning for information page, default 300 sec. [printer counter and drum usage sensors] (optional)

Configuration example:

brother_printer_status:
  module: brother_printer_status
  class: BrotherPrinterStatus
  host: !secret brother_hostname
  status_interval: 5
  info_interval: 600

"""

import appdaemon.plugins.hass.hassapi as hass
from requests import get
from datetime import datetime
import re

class BrotherPrinterStatus(hass.Hass):

    def initialize(self):

        __version__ = '0.2'

        self.MAX_IMAGE_HEIGHT = 56  # the maximum value of the height of the black image on the printer's webpage
        self.INFO_URL = '/general/information.html'
        self.STATUS_URL = '/general/status.html'

        try:
            if self.args['host']:
                self.host = self.args['host']
        except KeyError:
            self.error('Wrong arguments! You must supply a valid printer hostname or IP address.')
            return
        try:
            if 'status_interval' in self.args:
                status_interval = int(self.args['status_interval'])
            else:
                status_interval = 10
        except ValueError:
            self.error('Wrong arguments! Argument status_interval has to be an integer.')
            return
        try:
            if 'info_interval' in self.args:
                info_interval = int(self.args['info_interval'])
            else:
                info_interval = 300
        except ValueError:
            self.error('Wrong arguments! Argument info_interval has to be an integer.')
            return

        self.run_every(self.update_printer_status_page, datetime.now(), status_interval)
        self.run_every(self.update_printer_info_page, datetime.now(), info_interval)

    def update_printer_status_page(self, kwargs):
        self.download_page('http://{}{}'.format(self.host, self.STATUS_URL))
        if self.page:
            pattern = r'<dd>.+>([A-Za-z\s]+)</.+</dd>'
            regex = re.findall(pattern, self.page.text)
            try:
                status = regex[0].lower().rstrip()
            except IndexError:
                return
            attributes = {"friendly_name": "Printer status", "icon": "mdi:printer"}
            self.update_sensor('sensor.printer_status', status, attributes)
            pattern = r'class=\"tonerremain\" height=\"(\d+)\" />'
            regex = re.findall(pattern, self.page.text)
            try:
                toner = round(int(regex[0]) / self.MAX_IMAGE_HEIGHT * 100)
            except (IndexError, TypeError):
                return
            attributes = {"friendly_name": "Remaining toner", "icon": "mdi:flask-outline", "unit_of_measurement": "%"}
            self.update_sensor('sensor.printer_toner', toner, attributes)

    def update_printer_info_page(self, kwargs):
        self.download_page('http://{}{}'.format(self.host, self.INFO_URL))
        if self.page:
            pattern = r'<dd>(\d+)</dd>'
            regex = re.findall(pattern, self.page.text)
            try:
                printer_counter = int(regex[0])
            except (IndexError, TypeError):
                return
            attributes = {"friendly_name": "Printer counter", "icon": "mdi:file-document", "unit_of_measurement": "p"}
            self.update_sensor('sensor.printer_counter', printer_counter, attributes)
            pattern = r'\((\d+)\.00%\)'
            regex = re.findall(pattern, self.page.text)
            try:
                drum_usage = 100 - int(regex[0])
            except (IndexError, TypeError):
                return
            attributes = {"friendly_name": "Drum usage", "icon": "mdi:chart-donut", "unit_of_measurement": "%"}
            self.update_sensor('sensor.printer_drum_usage', drum_usage, attributes)
    def update_sensor(self, entity, state, attributes):
        try:
            self.set_state(entity, state = state, attributes = attributes)
        except:
            return

    def download_page(self, url):
        self.page = None
        try:
            self.page = get(url, timeout = 2)
        except:
            self.error('Host {} unreachable or respond too slow!'.format(self.host))
            return
