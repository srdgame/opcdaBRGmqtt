#!/usr/bin/python
# -*- coding: UTF-8 -*-
import threading
import logging
import time
import os
import json
from opcdabrg.opcda import *


class OPCDATunnel(threading.Thread):
	def __init__(self, mqttpub):
		threading.Thread.__init__(self)
		self._mqttpub = mqttpub
		self._opctunnel_isrunning = False
		self._opcConfig = None
		self._opcdaclient = None
		self._count = 0
		self.mqtt_clientid = None
		self._thread_stop = False

	def get_opcConfig(self):
		return self._opcConfig

	def start_opctunnel(self, opcConfig):
		self._opcConfig = opcConfig
		self.mqtt_clientid = opcConfig.get('clientid')
		self._opctunnel_isrunning = True

	def get_opcDatas(self):
		opcClient = OpenOPC.client()
		try:
			opcClient.connect(self._opcConfig.get('opcname'), self._opcConfig.get('opchost') or 'localhost')
		except Exception as ex:
			logging.warning('connect OPCDA Server err!err!err!')
			logging.exception(ex)
		if opcClient.isconnected:
			try:
				datas = opcClient.read(self._opcConfig.get('tags'), sync=True)
				opcClient.close()
				return datas
			except Exception as ex:
				logging.warning('readItem err!err!err!')
				logging.exception(ex)
				opcClient.close()
		else:
			return None

	def set_opcDatas(self):
		return True

	def opctunnel_pause(self):
		self._opctunnel_isrunning = False
		return True

	def opctunnel_resume(self):
		self._opctunnel_isrunning = True
		return True

	def opctunnel_clean(self):
		if self._opcdaclient.isconnected:
			self._opcdaclient.close()
		self._opctunnel_isrunning = None
		self._opcConfig = None
		return True

	def opctunnel_isrunning(self):
		return self._opctunnel_isrunning

	def run(self):
		if not os.path.exists("userdata"):
			os.mkdir("userdata")
		if os.path.exists("userdata/opcconfig.csv"):
			csvdatas = load_csv('userdata/opcconfig.csv')
			if csvdatas:
				self.start_opctunnel(csvdatas)
		self._opcdaclient = OpenOPC.client()
		if self._opcConfig:
			try:
				self._opcdaclient.connect(self._opcConfig.get('opcname'), self._opcConfig.get('opchost') or 'localhost')
			except Exception as ex:
				logging.warning('connect OPCDA Server err!err!err!')
				logging.exception(ex)
				self._mqttpub.opcdabrg_log_pub(self.mqtt_clientid, str(ex))
		while not self._thread_stop:
			if not self._opctunnel_isrunning:
				time.sleep(1)
				continue
			elif self._opcdaclient.isconnected:
				self._count = 0
				try:
					datas = self._opcdaclient.read(self._opcConfig.get('tags'), sync=True)
					self._mqttpub.opcdabrg_datas(self.mqtt_clientid, json.dumps(datas))
				except Exception as ex:
					logging.warning("read item's data err!err!err!")
					logging.exception(ex)
					self._mqttpub.opcdabrg_log_pub(self.mqtt_clientid, str(ex))
					self._opcdaclient.close()
					self._opcdaclient = OpenOPC.client()
				finally:
					time.sleep(1)
			else:
				try:
					self._opcdaclient.connect(self._opcConfig.get('opcname'), self._opcConfig.get('opchost') or 'localhost')
				except Exception as ex:
					logging.warning('connect OPCDA Server err!err!err!')
					logging.exception(ex)
					self._mqttpub.opcdabrg_log_pub(self.mqtt_clientid, str(ex))
					time.sleep(1 + 5 * self._count)
					self._count = self._count + 1

	def stop(self):
		self._thread_stop = True
		self.join()