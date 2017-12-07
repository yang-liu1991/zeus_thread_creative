#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Author: liuyang@domob.cn
Created Time: 2016-08-13 14:19:23
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
from db.models import ThAdcreatives 


basedir = path.realpath(path.join(path.dirname(__file__), '..'))
os.chdir(basedir)
sys.path.append(path.join(basedir, 'lib'))
exitFlag = 0

class ThreadCreativeCollect(threading.Thread):
	def __init__(self, account_queue, access_token):
		threading.Thread.__init__(self)
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')
		self.access_token = access_token
		self.object	= 'thread_creative_collect'
		self.account_queue	= account_queue
		self.working	= True
		self.app_details = {}
		

	
	"""
	根据adaccount_id获取adaccount_status
	1 = ACTIVE
	2 = DISABLED
	3 = UNSETTLED
	"""
	def getAdAccountInfoByAccountId(self, adaccount_id, access_token):
		try:
			requestUrl = 'https://graph.facebook.com/v2.9/act_%s' % (adaccount_id)
			requestParams	= {
				"fields":"account_id,account_status,spend_cap,amount_spent",
				"access_token":access_token
			}
			results = RequestApi().requestSend(requestUrl, requestParams)
			if results:
				self.logger.info('[getAdAccountInfoByAccountId] success,  adaccount_id:%s, sendurl:%s, results:%s' % (adaccount_id, requestUrl, results))
				return results
			raise Exception('getAdAccountInfoByAccountId exception!')
		except Exception, why:
			self.wflogger.exception('[getAdAccountInfoByAccountId] error, url:%s, adaccount_id:%s, reason:%s' % (requestUrl, adaccount_id, why))
			return False



	"""
	根据campaign_id获取Ads
	如果传入next_url，则直接请求next_url，否则为默认请求
	"""
	def getAdsByCampaignId(self, campaign_id, access_token, next_url=None):
		try:
			if not next_url:
				requestUrl = 'https://graph.facebook.com/v2.9/%s/ads' % (campaign_id)
				requestParams = {
					"fields":"id,name,status,adset_id,adcreatives{image_url,status,name,title,body,object_story_spec}", 
					"access_token":access_token
				}
				results = RequestApi().requestSend(requestUrl, requestParams)
			else:
				requestUrl = next_url
				results = RequestApi().requestSend(requestUrl)

			if results:
				self.logger.info('[getAdsByCampaignId] success,  campaign_id:%s, access_token:%s, sendurl:%s, results:%s' % (campaign_id, access_token, requestUrl, results))
				return results
			raise Exception('getAdsByCampaignId exception, results :False!') 
		except Exception, why:
			self.wflogger.exception('[getAdsByCampaignId] Exception, campaign_id:%s, access_token:%s, sendurl:%s, reason:%s' % (campaign_id, access_token, requestUrl, why))
			return False


	
	"""
	根据adsets_id获取adset
	"""
	def getAdsetsById(self, adset_id, access_token):
		try:
			requestUrl = 'https://graph.facebook.com/v2.9/%s' % (adset_id)
			requestParams = {
				"fields":"id,name,promoted_object,start_time,status", 
				"access_token":access_token
			}
			results = RequestApi().requestSend(requestUrl, requestParams)

			if results:
				self.logger.info('[getAdsetsById] success,  adset_id:%s, access_token:%s, sendurl:%s, results:%s' % (adset_id, access_token, requestUrl, results))
				return results
			raise Exception('getAdsetsById exception, results :%s' % results) 
		except Exception, why:
			self.wflogger.exception('[getAdsetsById] Exception, adset_id:%s, access_token:%s, sendurl:%s, reason:%s' % (adset_id, access_token, requestUrl, why))
			return False


	"""
	根据account_id获取campaigns
	"""
	def getCampaignByAccountId(self, account_id, access_token):
		try:
			requestUrl = 'https://graph.facebook.com/v2.9/act_%s' % (account_id)
			requestParams = {
				"fields":"account_id,campaigns{id,name,status}", 
				"access_token":access_token
			}
			results = RequestApi().requestSend(requestUrl, requestParams)
			self.logger.info('[getCampaignByAccountId] account_id:%s, access_token:%s, sendurl:%s, params:%s, results:%s' % \
				(account_id, access_token, requestUrl, requestParams, results))
			return results
		except Exception, why:
			self.wflogger.exception('[getCampaignByAccountId] Exception, account_id:%s, access_token:%s, sendurl:%s, params:%s, reason:%s' % \
				(account_id, access_token, requestUrl, requestParams, why))
			return False


	
		
	"""
	判断创意是否已经存在，不存在添加，存在则更新
	"""
	def __findAdCreative(self, adaccount_id, ad_info):
		try:
			adCreativeObj = ThAdcreatives.objects.filter(account_id=adaccount_id, ad_id=ad_info["ad_id"], creative_id=ad_info['creative_id'])
			self.logger.info('[__findAdCreative] success adaccount_id:%s, ad_info:%s, adCreativeObj:%s' % (adaccount_id, ad_info, adCreativeObj))
			if adCreativeObj:
				return adCreativeObj
			return False
		except Exception, why:
			self.wflogger.exception('[__findAdCreative] Exception, adaccount_id:%s, ad_id:%s, creative_id:%s, reason:%s' % \
				(adaccount_id, ad_info["ad_id"], ad_info["creative_id"], why))
			return False


	"""
	添加AdCreative信息
	"""
	def __insertAdCreative(self, adaccount_id, ad_info):
		try:
			insertTimestamp = int(time.time())
			adCreativeObj = ThAdcreatives(
				account_id		= adaccount_id,
				ad_id			= ad_info["ad_id"],
				creative_id		= ad_info["creative_id"],
				ad_name			= ad_info["ad_name"],
				ad_message		= ad_info["ad_message"],
				image_url		= ad_info["image_url"],
				start_time		= ad_info["start_time"],
				promoted_url	= ad_info["promoted_url"],
				app_details		= ad_info["app_details"],
				created_at		= insertTimestamp,
				updated_at		= insertTimestamp
				)
			adCreativeObj.save()
			self.logger.info('[__insertAdCreative] success adaccount_id:%s, ad_info:%s' % (adaccount_id, ad_info))
			return True
		except Exception, why:
			self.wflogger.exception('[__insertAdCreative] Exception, adaccount_id:%s, ad_info:%s, reason:%s' % (adaccount_id, ad_info, why))
			return False


	"""
	更新AdCreative信息
	"""
	def __updateAdCreative(self, adaccount_id, ad_info):
		try:
			updateTimestamp = int(time.time())
			adCreativeObj = ThAdcreatives.objects.filter(
					account_id=adaccount_id, 
					ad_id=ad_info['ad_id'], 
					creative_id=ad_info['creative_id']).update(
						ad_name		= ad_info['ad_name'],
						ad_message	= ad_info["ad_message"],
						image_url	= ad_info['image_url'],
						start_time	= ad_info["start_time"],
						promoted_url= ad_info["promoted_url"],
						app_details	= ad_info['app_details'],
						updated_at	= updateTimestamp
					)
			self.logger.info('[__updateAdCreative] success adaccount_id:%s, ad_info:%s' % (adaccount_id, ad_info))
			return True
		except Exception, why:
			self.wflogger.exception('[__updateAdCreative] Exception, adaccount_id:%s, ad_info:%s, reason:%s' % (adaccount_id, ad_info, why))
			return False


	"""
	整合creatives
	"""
	def __buildAdInfo(self, ad_obj, adcreative):
		#判断adset状态和adcreative状态
		if adcreative['status'] != 'ACTIVE':
			return False
	
		ad_info = {}
		#获取广告开启时间
		if ad_obj.has_key('start_time'):
			start_time					= ad_obj['start_time']
			strtimeArray				= time.strptime(start_time[0:19], "%Y-%m-%dT%H:%M:%S")
			ad_info['start_time']		= int(time.mktime(strtimeArray)) + 3600 * 8
		else:
			ad_info['start_time']		= ''

		#获取推广的url
		if ad_obj.has_key('promoted_url'):
			ad_info['promoted_url']		= ad_obj['promoted_url']
			if not ad_info['promoted_url']: return False
			#获取推广url的app信息
			app_details	= self.__getAppDetails(ad_info['promoted_url'])
			if app_details: 
				ad_info['app_details']	= json.dumps(app_details)
			else:
				ad_info['app_details']	= ''
		else:
			return False

		#获取创意链接
		if adcreative.has_key('image_url'):
			ad_info['image_url']		= adcreative['image_url']
		else:
			ad_info['image_url']		= ''
		
		#获取创意id
		if adcreative.has_key('id'):
			ad_info['creative_id']		= adcreative['id']
		else:
			ad_info['creative_id']		= ''

		#获取ad id
		if ad_obj.has_key('id'):
			ad_info['ad_id']			= ad_obj['id']
		else:
			ad_info['ad_id']			= ''

		#获取ad name
		if ad_obj.has_key('name'):
			ad_info['ad_name']			= ad_obj['name']
		else:
			ad_info['ad_name']			= ''

		#获取广告语
		if adcreative.has_key('object_story_spec'):
			object_story_spec = adcreative['object_story_spec']
			if object_story_spec.has_key('link_data'):
				link_data = object_story_spec['link_data']
				if link_data.has_key('message'):
					#将16进制转换成2进制表示，不然数据库保存出错
					ad_info['ad_message']		= binascii.b2a_hex(link_data['message'])
				else:
					ad_info['ad_message']       = ''
			else:
				ad_info['ad_message']       = ''
		else:
			ad_info['ad_message']		= ''
		return ad_info



	"""
	获取app details的方法
	"""
	def __getAppDetails(self, promoted_url):
		try:
			#如果已经抓取过的链接，直接从内存中返回
			if self.app_details.has_key(promoted_url):
				return self.app_details[promoted_url]

			app_details_info = ParsingPackage(promoted_url).get_app_details()
			if app_details_info:
				self.app_details[promoted_url]	= app_details_info
				self.logger.info('__getAppDetails Success, promoted_url:%s, app_details_info:%s' % (promoted_url, app_details_info))
				return app_details_info
			raise Exception('__getAppDetails failed')
		except Exception, why:
			self.wflogger.exception('[__getAppDetails] Exception, promoted_url:%s, app_details_info:%s, reason:%s' % \
				(promoted_url, app_details_info, why))
			return False


	"""
	开始干活
	"""
	def __beginWork(self, account_id):
		try:
			access_token	= self.access_token
			#如果帐户已经被disabled，直接忽略
			adAccountInfo	= self.getAdAccountInfoByAccountId(account_id, access_token)
			if adAccountInfo:
				adAccountObj = json.loads(adAccountInfo)
				adAccountStatus = 0  if "account_status" not in adAccountObj else adAccountObj['account_status']
				adAccountSpendCap = 0 if "spend_cap" not in adAccountObj else int(adAccountObj['spend_cap'])
				adAccountAmountSpent = 0 if "amount_spent" not in adAccountObj else int(adAccountObj['amount_spent'])
				if adAccountStatus != 1 or adAccountSpendCap - adAccountAmountSpent <= 0 : return
			#获取campaign 数据，如果campaign没有开户则忽略
			adCampaigns	= self.getCampaignByAccountId(account_id, access_token)
			if adCampaigns:
				adCampaignsList = json.loads(adCampaigns)
				# 如果获取不到campaign数据，则忽略
				if not adCampaignsList.has_key('campaigns') : return
				campaignsData = adCampaignsList['campaigns']['data']
				for campaigns in campaignsData:
					# 如果campaigns状态非ACTIVE则忽略
					if campaigns['status'] != 'ACTIVE': break
					campaignId	= campaigns['id']
					adsResult = self.getAdsByCampaignId(campaignId, access_token)
					adsObj	= json.loads(adsResult)
					if adsObj.has_key('data'):
						for ad in adsObj['data']:
							# 如果ad 状态非ACTIVE则忽略
							if ad['status'] != 'ACTIVE' : break
							ad_obj = {}
							ad_obj['id']		= ad['id']
							ad_obj['name']		= ad['name']
							adcreatives	= ad['adcreatives']
							adSetsResult		= self.getAdsetsById(ad['adset_id'], access_token)
							if not adSetsResult: break
							adSets		= json.loads(adSetsResult)
							if adSets: 
								# 如果adsets状态非ACTIVE则忽略
								if adSets['status'] != 'ACTIVE': break
								if adSets.has_key('promoted_object'):
									promoted_object = adSets['promoted_object']
									if promoted_object.has_key('object_store_url'):
										ad_obj['promoted_url']	= promoted_object['object_store_url']
									else:
										ad_obj['promoted_url']	= ''
								else:
									ad_obj['promoted_url']  = ''
								ad_obj['start_time']	= adSets['start_time']
							else:
								break
							for adcreative in adcreatives['data']:
								ad_info	= self.__buildAdInfo(ad_obj, adcreative)
								if not ad_info: break
								#判断创意是否存在，存在则更新，不存在则添加
								adCreativeObj = self.__findAdCreative(account_id, ad_info)
								if adCreativeObj:
									self.__updateAdCreative(account_id, ad_info)
								else:
									self.__insertAdCreative(account_id, ad_info)
				if adCampaignsList.has_key('paging'):
					paging		= adCampaignsList['paging']
					while paging.has_key('next'):
						nextUrl	= RequestApi().requestUrlRebuild(paging['next'], {'limit':'100'})
						results = self.self.getCampaignByAccountId(account_id, access_token, nextUrl)
						adCampaigns	= self.getCampaignByAccountId(account_id, access_token)
						if adCampaigns:
							adCampaignsList = json.loads(adCampaigns)
							# 如果获取不到campaign数据，则忽略
							if not adCampaignsList.has_key('campaigns') : return
							campaignsData = adCampaignsList['campaigns']['data']
							for campaigns in campaignsData:
								if campaigns['status'] != 'ACTIVE': break
								campaignId	= campaigns['id']
								adsResult = self.getAdsByCampaignId(campaignId, access_token)
								adsObj	= json.loads(adsResult)
								if adsObj.has_key('data'):
									for ad in adsObj['data']:
										if ad['status'] != 'ACTIVE' : break
										ad_obj = {}
										ad_obj['id']		= ad['id']
										ad_obj['name']		= ad['name']
										adcreatives	= ad['adcreatives']
										adSetsResult        = self.getAdsetsById(ad['adset_id'], access_token)
										if not adSetsResult: break
										adSets      = json.loads(adSetsResult)
										if adSets: 
											if adSets['status'] != 'ACTIVE': break
											if adSets.has_key('promoted_object'):
												promoted_object = adSets['promoted_object']
												if promoted_object.has_key('object_store_url'):
													ad_obj['promoted_url']	= promoted_object['object_store_url']
												else:
													ad_obj['promoted_url']	= ''
											else:
												ad_obj['promoted_url']  = ''
											ad_obj['start_time']	= adSets['start_time']
										else:
											continue
										for adcreative in adcreatives['data']:
											ad_info	= self.__buildAdInfo(ad_obj, adcreative)
											if not ad_info: break
											#判断创意是否存在，存在则更新，不存在则添加
											adCreativeObj = self.__findAdCreative(account_id, ad_info)
											if adCreativeObj:
												self.__updateAdCreative(account_id, ad_info)
											else:
												self.__insertAdCreative(account_id, ad_info)
			return True
		except Exception, why:
			self.logger.exception('[__beginWork] Exception, account_id:%s, reason:%s' % (account_id, why))
			return False



	"""
	子线程控制器
	"""
	def run(self):
		while True:
			try:
				queueEmpty	= False
				(account_id, business_id)	= self.account_queue.get(False)
				self.__beginWork(account_id)
				self.account_queue.task_done()	
				self.logger.info('[ThreadCreativeCollect] account_id:%s, thread name:%s, qsize:%d' % 
					(account_id, threading.currentThread().getName(), self.account_queue.qsize()))
			except Queue.Empty, why:
				self.logger.info('[%s] Info, account_queue size is Empty!' % 'run')
				return False
			except Exception, why:
				self.wflogger.exception('account_id :%s, exception, reason:%s' % (account_id, why))
				self.account_queue.task_done()	
			

# vim: set noexpandtab ts=4 sts=4 sw=4 :
