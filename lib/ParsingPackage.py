#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Author: liuyang@xxx.cn
Created Time: 2017-04-11 11:05:09
Desc : 此类主要的作用为抓取google play和Appstore的信息，用于数据收集。
"""


import os
import re
import sys
import json
import urlparse
import requests
import logging
import logging.config
from os import path
from bs4 import BeautifulSoup
#from RequestApi	import RequestApi

basedir = path.realpath(path.join(path.dirname(__file__), '..'))
os.chdir(basedir)
sys.path.append(path.join(basedir, 'lib'))


class ParsingPackage(object):
	def __init__(self, promoted_url):
		"""
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')
		"""
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')
		self.promoted_url	= promoted_url
	
	
	"""
	获取google play的api
	"""
	def __get_googleplay_api(self):
		return 'https://play.google.com/store/apps/details'


	"""
	获取appstore信息的api
	"""
	def __get_appstore_api(self):
		return 'http://itunes.apple.com/lookup'


	"""
	获取iTunes的app id
	"""
	def __get_appstore_id(self):
		try:
			appstore_mode = re.compile(r'\d+').findall(self.promoted_url)
			appstore_id = appstore_mode[0]
			if appstore_id: return appstore_id
			raise Exception('Not iTunes url, promoted_url:%s' % self.promoted_url)
		except Exception, why:
			self.wflogger.exception('[__get_appstore_id] Exception, promoted_url:%s, reason:%s' % \
				self.promoted_url, why)
			return False


	"""
	获取google play的app id
	"""
	def __get_google_play_id(self):
		try:
			url_split_result = urlparse.urlsplit(self.promoted_url)
			url_query_result = urlparse.parse_qs(url_split_result.query, True)
			google_play_id = url_query_result['id'][0]
			if google_play_id: return google_play_id
			raise Exception('Not google play url, promoted_url:%s' % self.promoted_url)
		except Exception, why:
			self.wflogger.exception('[__get_google_play_id] Exception, promoted_url:%s, reason:%s' % \
				(self.promoted_url, why))
			return False


	
	"""
	获取goolge play的app details信息
	"""
	def __get_googleplay_details(self):
		try:
			google_play_id = self.__get_google_play_id()
			google_play_info = {}
			if google_play_id:
				google_play_api = self.__get_googleplay_api()
				response = requests.get(google_play_api, params={'id':google_play_id})
				soup_object = BeautifulSoup(response.text, 'lxml')	
				# 获取产品名称
				try:
					google_play_info['app_name'] = soup_object.find(class_='id-app-title').string
				except Exception, why:
					self.wflogger.exception('[__get_googleplay_details] get app name error, promoted_url:%s, reason:%s' % (self.promoted_url, why))
					google_play_info['app_name']= ''

				#获取业务类型
				try:
					primary_subtitle_info = soup_object.find(class_='document-subtitle primary')
					for i in primary_subtitle_info: 
						primary_category = i.next_sibling.string
						break
					category_subtitle_info = soup_object.find(class_='document-subtitle category')
					for i in category_subtitle_info:
						subtitle_category = i.next_sibling.string
						break
					google_play_info['category'] =  {'primary_category':primary_category, 'subtitle_category':subtitle_category}
				except Exception, why:
					self.wflogger.exception('[__get_googleplay_details] get subtitle error, promoted_url:%s, reason:%s' % (self.promoted_url, why))
					google_play_info['category'] = {'primary_category':'', 'subtitle_category':''}
				
				#获取开发者信息
				try:
					google_play_info['developer'] = soup_object.find(class_="content contains-text-link").text.strip().replace('\n', ' ').replace('\r\n', ' ')
				except Exception, why:
					self.wflogger.exception('[__get_googleplay_details] get developer error, promoted_url:%s, reason:%s' % (self.promoted_url, why))
					google_play_info['developer'] = ''
			
				#获取安装次数
				try:
					google_play_info['install_number'] = soup_object.find(itemprop="numDownloads").text.strip()
				except Exception, why:
					self.wflogger.exception('[__get_googleplay_details] get install_number error, promoted_url:%s, reason:%s' % (self.promoted_url, why))
					google_play_info['install_number'] = ''

				#获取更新日期
				try:
					google_play_info['update_time'] = soup_object.find(itemprop="datePublished").text.strip()
				except Exception, why:
					self.wflogger.exception('[__get_googleplay_details] get date_published error, promoted_url:%s, reason:%s' % (self.promoted_url, why))
					google_play_info['update_time'] = ''
			self.logger.info('[__get_googleplay_details] promoted_url:%s, google_play_info:%s' % (self.promoted_url, google_play_info))
			return google_play_info
		except Exception, why:
			self.wflogger.exception('[__get_googleplay_details] Exception, promoted_url:%s, reason:%s' % (self.promoted_url, why))
			return False



	"""
	获取iTunes Appstore的app details
	"""
	def __get_appstore_details(self, country='cn'):
		try:
			appstore_id = self.__get_appstore_id()
			appstore_info = {}
			response = requests.get(self.__get_appstore_api(), {'id':appstore_id}, verify=False)
			appstore_obj = json.loads(response.text)
			if appstore_obj.has_key('results'):
				self.logger.info('__get_appstore_details promoted_url:%s, response:%s, results:%s' % (self.promoted_url, response, appstore_obj['results']))
				if appstore_obj['resultCount'] == 1:
					results = appstore_obj['results'][0]
				else:
					raise Exception('__get_appstore_details error, promoted_url:%s, response:%s' % (self.promoted_url, response))
				#获取产品名称
				if results.has_key('trackCensoredName'):
					appstore_info['app_name']	= results['trackCensoredName']
				else:
					appstore_info['app_name']	= ''

				#获取业务类型
				if results.has_key('primaryGenreName'):
					primary_category = results['primaryGenreName']
					appstore_info['category']	= {'primary_category':primary_category}
				else:
					appstore_info['category']	= {'primary_category':''}

				#获取开发者信息
				if results.has_key('sellerName'):
					appstore_info['developer']	= results['sellerName']
				else:
					appstore_info['developer']	= ''

				#安装次数..

				#获取更新日期
				if results.has_key('releaseDate'):
					appstore_info['update_time']	= results['releaseDate']
				else:
					appstore_info['update_time']	= ''
				#获取应用内商品价格
				purchases = self.__get_appstore_purchases()
				if purchases:
					appstore_info['purchases']		= str(purchases)
				else:
					appstore_info['purchases']		= ''
				self.logger.info('[__get_appstore_details] promoted_url:%s, appstore_info:%s' % (self.promoted_url, appstore_info))
				return appstore_info
			raise Exception('__get_appstore_details json load failed, response:%s' % response.text)
		except Exception, why:
			self.wflogger.exception('[__get_appstore_details] Exception, promoted_url:%s, reason:%s' % (self.promoted_url, why))
			return False


	"""
	获取appstore的 Purchases
	"""
	def __get_appstore_purchases(self):
		try:
			response = requests.get(self.promoted_url, verify=False)
			soup_obj = BeautifulSoup(response.text, 'lxml')
			purchases =	soup_obj.find(class_="in-app-purchases").ol
			return purchases
		except Exception, why:
			self.wflogger.exception('[__get_appstore_purchases] Exception, promoted_url:%s, reason:%s' % \
				(self.promoted_url, why))
			return False


	"""
	对外提供的方法，返回获取到的app details
	"""
	def get_app_details(self):
		try:
			match_itunes = re.search(r'itunes.apple.com', self.promoted_url)
			match_google = re.search(r'play.google.com', self.promoted_url)
			if match_itunes:
				return self.__get_appstore_details()
			elif match_google:
				return self.__get_googleplay_details()
			else:
				raise Exception('get_app_details failed unknow url!')
		except Exception, why:
			self.wflogger.exception('[get_app_details] Exception, promoted_url:%s, reason:%s' % (self.promoted_url, why))
			return False


# vim: set noexpandtab ts=4 sts=4 sw=4 :
