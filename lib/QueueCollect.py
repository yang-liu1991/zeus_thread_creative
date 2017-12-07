#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Author: liuyang@domob.cn
Created Time: 2017-04-18 17:50:57
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
import binascii
from os import path
from datetime import datetime
from RequestApi	import RequestApi
from ParsingPackage import ParsingPackage
from multiprocessing import Process, JoinableQueue, cpu_count


basedir = path.realpath(path.join(path.dirname(__file__), '..'))
os.chdir(basedir)
sys.path.append(path.join(basedir, 'lib'))
exitFlag = 0



class QueueCollect(threading.Thread):
	def __init__(self, access_token):
		threading.Thread.__init__(self)
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')
		self.access_token = access_token
		self.account_queue = JoinableQueue()
		self.api_version = 'v2.9'
		self.class_name	= self.__class__.__name__


	"""
	通过access_token获取所有可以读取的accounts信息
	"""
	def getAdAccounts(self, access_token, next_url=None):
		try:
			if not next_url:
				requestUrl = 'https://graph.facebook.com/%s/me' % self.api_version
				requestParams = {
					"fields":"adaccounts",
					"access_token":access_token
				}
				results = RequestApi().requestSend(requestUrl, requestParams)
			else:
				requestUrl = next_url
				results = RequestApi().requestSend(requestUrl)
			if results:
				self.logger.info('[getAdAccounts] Success, requestUrl:%s, results:%s' % (requestUrl, results))
				return results
			raise Exception('getAdAccounts exception, results :False!')
		except Exception, why:
			self.wflogger.exception('[getAdAccounts] Exception, requestUrl:%s, reason:%s' % (requestUrl, why))
			return False


	"""
	根据access_token获取相应的business id
	"""
	def get_bmid_by_access_token(self, access_token):
		retry = 0
		while retry < 3:
			try:
				bm_id_dict = {}
				response = requests.get(
					'https://graph.facebook.com/%s/me/businesses' % (self.api_version),
					params={'access_token':access_token}
				)
				ret = json.loads(response.text)
				self.logger.info('[%s] [%s] access_token:%s, ret:%s' % (self.class_name, 'get_bmid_by_access_token', access_token, ret))
				if ret:
					for item in ret['data']:
						bm_id_dict[item['id']]	= access_token
					self.logger.info('[%s] [%s] response:%s, bm_id_dict:%s' % \
						(self.class_name, 'get_bmid_by_access_token', response, bm_id_dict))
					return bm_id_dict
				raise Exception('Response json load Exception!')
			except Exception, why:
				retry += 1
				self.wflogger.exception('[%s] [%s] Exception, access_token:%s, response:%s, reason:%s, retry:%d' % \
					(self.class_name, 'get_bmid_by_access_token', access_token, response, why, retry))
		return False


	
	"""
	根据bm id 获取对应的account id, 加入到队列中
	"""
	def get_accounts_by_bmid(self, business_id, access_token, next_url=''):
		retry = 0
		while retry < 3:
			try:
				if not next_url:
					response = requests.get(
						'https://graph.facebook.com/%s/%s/owned_ad_accounts' % (self.api_version, business_id),
						params={'access_token':access_token}
					)
				else:
					response = requests.get(next_url)
				ret = json.loads(response.text)
				self.logger.info('[%s] [%s] business_id:%s, access_token:%s, next_url:%s, ret:%s' % \
					(self.class_name, 'get_accounts_by_bmid', business_id, access_token, next_url, ret))
				if ret:
					for key, item in ret.iteritems():
						if key == 'data' and item != '':
							for account_info in item:
								self.account_queue.put((account_info['account_id'], business_id))
						elif key == 'paging' and 'next' in item:
							next_url = self.rebuild_request_params(item['next'], {'limit':'500'})
							self.get_accounts_by_bmid(business_id, access_token, next_url)
					return True
				else:
					raise Exception('Response json load Exception!')
			except Exception, why:
				retry += 1
				self.wflogger.exception('[%s] [%s] Exceptioin, business_id:%s, access_token:%s, next_url:%s, why:%s, retry:%d' % \
					(self.class_name, 'get_accounts_by_bmid', business_id, access_token, next_url, why, retry))
		return False



	"""
	重组url参数，主要是对limit进行重写
	"""
	def	rebuild_request_params(self, url, params):
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
			self.logger.info('[%s] [rebuild_request_params] url:%s, params:%s, rebuildUrl:%s' % \
				(self.class_name, url, params, rebuildUrl))
			return rebuildUrl
		except Exception, why:
			self.wflogger.exception('[%s] [rebuild_request_params] Exception, url:%s, params:%s, reason:%s' % \
				(self.class_name, url, params, why))
			return url		
	

	
# vim: set noexpandtab ts=4 sts=4 sw=4 :
