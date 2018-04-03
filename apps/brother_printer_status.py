"""
Adds four sensors to HA with data from brother network printer WWW interface.
Tested only with Brother HL-L2340DW.
Arguments:
 - host					- hostname or IP address of the printer (required)
 - status_interval		- interval scanning for status page, default 10 sec.
                          [status and remain toner sensors] (optional)
 - info_interval		- interval scanning for information page, default 300
                          sec. [printer counter and drum usage sensors]
                          (optional)

Configuration example:

brother_printer_status:
  module: brother_printer_status
  class: BrotherPrinterStatus
  host: !secret brother_hostname
  status_interval: 5
  info_interval: 600

"""

import appdaemon.plugins.hass.hassapi as hass
import requests
from datetime import datetime
import re

class BrotherPrinterStatus(hass.Hass):

    def initialize(self):

        __version__ = '0.2.2'

        # max value of the height of the black image on the printer's webpage
        self.MAX_IMAGE_HEIGHT = 56
        self.INFO_URL = "/general/information.html"
        self.STATUS_URL = "/general/status.html"

        try:
            if self.args['host']:
                self.host = self.args['host']
        except KeyError:
            self.error("Wrong arguments! You must supply a valid printer " \
                       "hostname or IP address.")
            return
        try:
            if 'status_interval' in self.args:
                status_interval = int(self.args['status_interval'])
            else:
                status_interval = 10
        except ValueError:
            self.error("Wrong arguments! Argument status_interval has to be " \
                       "an integer.")
            return
        try:
            if 'info_interval' in self.args:
                info_interval = int(self.args['info_interval'])
            else:
                info_interval = 300
        except ValueError:
            self.error("Wrong arguments! Argument info_interval has to be an " \
                       "integer.")
            return

        self.run_every(self.update_printer_status_page, datetime.now(), \
                       status_interval)
        self.run_every(self.update_printer_info_page, datetime.now(), \
                       info_interval)

    def update_printer_status_page(self, kwargs):
        page = self.download_page("http://{}{}".format(self.host,
                                                       self.STATUS_URL))
        if page:
            regex_res = self.regex(r"<dd>.*>(\w+\s?\w+)\s+<.*</dd>", page)
            if regex_res:
                status = regex_res.lower()
                if status:
                    attributes = {"friendly_name": "Printer status", \
                                  "icon": "mdi:printer"}
                    self.set_state('sensor.printer_status', state = status, \
                                   attributes = attributes)
            regex_res = self.regex(r"class=\"tonerremain\" height=\"(\d+)\"", \
                                   page)
            if regex_res:
                try:
                    toner = round(int(regex_res) / self.MAX_IMAGE_HEIGHT * 100)
                except TypeError:
                    return
                if toner:
                    attributes = {"friendly_name": "Remaining toner", \
                                  "icon": "mdi:flask-outline", \
                                  "unit_of_measurement": "%"}
                    self.set_state('sensor.printer_toner', state = toner, \
                                   attributes = attributes)

    def update_printer_info_page(self, kwargs):
        page = self.download_page("http://{}{}".format(self.host, \
                                                       self.INFO_URL))
        if page:
            regex_res = self.regex(r"<dd>(\d+)</dd>", page)
            if regex_res:
                try:
                    counter = int(regex_res)
                except TypeError:
                    return
                if counter:
                    attributes = {"friendly_name": "Printer counter", \
                                  "icon": "mdi:file-document", \
                                  "unit_of_measurement": "p"}
                    self.set_state('sensor.printer_counter', state = counter, \
                                   attributes = attributes)
            regex_res = self.regex(r"\((\d+\.\d+)%\)", page)
            if regex_res:
                try:
                    drum_usage = round(100 - float(regex_res))
                except TypeError:
                    return
                if drum_usage:
                    attributes = {"friendly_name": "Drum usage", \
                                  "icon": "mdi:chart-donut", \
                                  "unit_of_measurement": "%"}
                    self.set_state('sensor.printer_drum_usage', \
                                   state = drum_usage, attributes = attributes)

    def download_page(self, url):
        page = None
        try:
            page = requests.get(url, timeout = 2)
        except requests.exceptions.RequestException:
            self.error("Host {} unreachable or respond too " \
                       "slow!".format(self.host))
            return
        return page.text

    def regex(self, pattern, text):
        resault = re.findall(pattern, text)
        if len(resault) > 0:
            return resault[0]
        return None
