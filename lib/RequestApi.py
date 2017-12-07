#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Author: liuyang@domob.cn
Created Time: 2016-11-02 15:04:13
"""

import sys
reload(sys)

sys.setdefaultencoding('UTF-8')

import ConfigParser
import requests
import logging
import logging.config
import time
import json
import os
import Queue
import threading
import urlparse
from os import path
from datetime import datetime

basedir = path.realpath(path.join(path.dirname(__file__), '..'))
os.chdir(basedir)
sys.path.append(path.join(basedir, 'lib'))

class RequestApi(object):

	def __init__(self):
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')

	"""
	封装POST方法
	接收请求url和params，如果请求成功返回请求结果，否则返回False
	"""
	def requestSend(self, url, params=None):
		retry = 0
		while retry < 3:
			try:
				result = requests.get(url, params=params)
				self.logger.info('[requestSend] sendUrl:%s' % (result.url))
				if result.status_code == 200:
					return result.text
				raise Exception('[requestSend] HttpException, result: %s' % (result))
			except Exception, why:
				retry += 1
				self.wflogger.exception('[requestSend] Exception, url:%s, params:%s, reason:%s, retry:%d' % \
					(url, params, why, retry))
				time.sleep(2)
		return False



	"""
	URL重组, 更新默认的返回参数limit
	"""
	def	requestUrlRebuild(self, url, params):
		try:
			result = urlparse.urlsplit(url)
			urlQuery = urlparse.parse_qs(result.query, True)
			for query in params:
				queryTmpList = []
				queryTmpList.append(params[query])
				urlQuery[query] = queryTmpList

			paramsList = []
			for query in urlQuery:
				queryValue = urlQuery[query]
				param = "%s=%s" % (query, queryValue[0].encode("utf-8"))
				paramsList.append(param)
			urlQuery = '&'.join(paramsList)
			rebuildUrl = urlparse.urlunsplit((result.scheme, result.netloc, result.path, urlQuery, result.fragment))
			self.logger.info('[requestUrlRebuild] url:%s, params:%s, rebuildUrl:%s' % (url, params, rebuildUrl))
			
			return rebuildUrl
		except Exception, why:
			self.wflogger.exception('[requestUrlRebuild] error, url:%s, params:%s, reason:%s' % (url, params, why))
			return url


# vim: set noexpandtab ts=4 sts=4 sw=4 :
