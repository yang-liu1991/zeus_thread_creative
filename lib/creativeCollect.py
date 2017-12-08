#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Author: vagrant@xxx.cn
Created Time: 2016-08-15 09:27:37
"""
import sys
reload(sys)

sys.setdefaultencoding('UTF-8')

import ConfigParser
import requests
import argparse
import datetime
import logging
import logging.config
import time
import json
import os
import Queue
import threading
from os import path
from RequestApi	import RequestApi
from QueueCollect import QueueCollect

#from django.conf import settings


basepath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basepath + '/lib')


class mainCollect(QueueCollect):
	def __init__(self, conf):
		self.logger		= logging.getLogger('threadCreativeCollect')
		self.wflogger	= logging.getLogger('threadCreativeCollect.wf')
		self.object		= 'thread_creative_collect'
		self.conf		= conf
		self.access_token	= self.conf.get("access_token", "access_token")
		super(mainCollect, self).__init__(self.access_token)
		self.working	= False

	
	

	"""
	初始化数据表，每次抓取之前先清除旧数据
	"""
	def deleteOldData(self, oldDataTime):
		try:
			ThAdcreatives.objects.filter(created_at__lte=oldDataTime).delete()
		except Exception, why:
			self.wflogger.exception('[deleteOldData] error oldDataTime:%d, reason:%s' % (oldDataTime, why))
			return False

	
	"""
	开启线程，执行任务
	"""
	def startToWork(self, access_token):
		from ThreadCreativeCollect import ThreadCreativeCollect
		threads = []
		threadAccountId = []
		self.working = True
		#设置线程数量
		print 'Queue collect qsize:%d' % self.account_queue.qsize()

		NUM_WORKERS	= 10
		for i in range(NUM_WORKERS):
			threadAccountId = ThreadCreativeCollect(self.account_queue, access_token)
			threadAccountId.setDaemon(True)
			threadAccountId.start()
			threads.append(threadAccountId)

		for thread in threads:
			thread.join() 

		self.account_queue.join()



	"""
	主线程控制方法，负责调用子线程
	"""
	def run(self):
		nowtime		= time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		nowTimestamp	= int(time.time())
		threeDaysAgoTimestamp	= nowTimestamp - 3600 * 24 * 3
		#adAccounts	= self.getAdAccount()
		#初始化数据表，删除旧数据(删除三天前数据)，重新抓取
		self.deleteOldData(threeDaysAgoTimestamp)

		print 'Getting thread creatives data...'
		access_token_list = [self.access_token]
		for access_token in access_token_list:
			business_ids = self.get_bmid_by_access_token(access_token)
			if business_ids:
				for business_id in business_ids:
					self.get_accounts_by_bmid(business_id, access_token)
		print 'account_queue size:%d' % self.account_queue.qsize()

		self.startToWork(self.access_token)
		print 'all task succeed!'
if __name__ == '__main__':
	ap = argparse.ArgumentParser(description = 'thread creative collector')
	ap.add_argument('-d', '--executeDir', type = str,
			help = 'app execution directory',
			default = basepath)
	ap.add_argument("-t", "--timestamp", type = str,
			help = "",
			default = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	args = ap.parse_args()

	print 'thread_creative_collect run at %s' % args.executeDir
	os.chdir(args.executeDir)
	sys.path.append(args.executeDir+'/conf')
	os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
	#加载日志配置文件
	logging.config.fileConfig(args.executeDir + '/conf/logging.cfg')
	#加载配置文件
	confPath = os.path.join(args.executeDir + '/conf/thread_creative_collect.cfg')
	conf = ConfigParser.RawConfigParser()
	conf.read(confPath)

	from db.models import ThAdcreatives 
	creativeCollect = mainCollect(conf)
	creativeCollect.run()

# vim: set noexpandtab ts=4 sts=4 sw=4 :
