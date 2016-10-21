# coding: utf-8
import leancloud
from leancloud import Engine
from leancloud import LeanEngineError

from app import app

from logentries import LogentriesHandler
import logging


from qiniu import Auth
from qiniu import BucketManager
import requests

import os
import json

import time

engine = Engine(app)

log = logging.getLogger('logentries')
log.setLevel(logging.INFO)
log.addHandler(LogentriesHandler(os.environ.get('logentries_key')))

access_key = os.environ.get('qiniu_ak')
secret_key = os.environ.get('qiniu_sk')
bucket_name = os.environ.get('qiniu_bn')
bucket_domain = os.environ.get('qiniu_bd')
q = Auth(access_key, secret_key)
bucket = BucketManager(q)

hook_url = os.environ.get('hook_url')
review_hook_url = os.environ.get('review_hook_url')

# local_time = time.localtime()
# # day_stamp = time.strftime("%Y-%m-%d")
# day_stamp = '20161013'
# collection = db['realtime_quotes_'+day_stamp]
datetime_format = "%Y-%m-%d %H:%M:%S"

granularity =10

def cache_sina_stock_gif(stock_code):
    if stock_code.startswith('60'):
        sina_code = 'sh'+stock_code
    else:
        sina_code = 'sz'+stock_code
    image_url = 'http://image.sinajs.cn/newchart/min/n/{sina_code}.gif'.format(sina_code=sina_code)

    ts = int(time.time())
    key = stock_code +'-'+str(ts) + '-sina.gif'

    ret, info = bucket.fetch(image_url, bucket_name, key)
    # log.info(stock_code+' '+str(info))
    if '200' in str(info)[0:50]:
        return bucket_domain+key
    else:
        return image_url

def alarming_bearychat(msg):
    stock_code = msg['stock_code']
    img_url = cache_sina_stock_gif(stock_code)
    src = u'新图' if 'sinajs' in img_url else  u'缓存'
    bearychat_msg ={
        "text": '**'+msg['name']+' '+ stock_code+'**\n>'+' | '.join(msg['time_list']),
        "markdown": True,
        "attachments": [{
            "text": msg['name']+u" 分时图 ("+ src +') '+time.strftime(datetime_format),
            "color": "#ff0000",
            "images": [{"url": img_url}]
        }]
    }
    headers = {
    'Content-Type': 'application/json'
    }
    requests.post(hook_url,headers = headers,data = json.dumps(bearychat_msg))

# def review_alarming_bearychat(msg):   #区别是多了一个 index，一个股票的所有提醒是一次发送的
#     stock_code = msg['stock_code']
#     img_url = cache_sina_stock_gif(stock_code)
#     src = u'新图' if 'sinajs' in img_url else  u'缓存'
#     bearychat_msg ={
#         "text": '**'+str(msg['index'])+'.'+msg['name']+' '+ stock_code+'**\n>'+' | '.join(msg['time_list']),
#         "markdown": True,
#         "attachments": [{
#             "text": msg['name']+u" 分时图 ("+ src +') '+time.strftime(datetime_format),
#             "color": "#ff0000",
#             "images": [{"url": img_url}]
#         }]
#     }
#     headers = {
#     'Content-Type': 'application/json'
#     }
#     log.info(json.dumps(bearychat_msg))
#     requests.post(review_hook_url,headers = headers,data = json.dumps(bearychat_msg))
def review_alarming_bearychat():   #区别是多了一个 index，一个股票的所有提醒是一次发送的
    bearychat_msg ={
        "text": u'今日复盘报告已经生成，请去 LeanCloud 查看！',
        "markdown": True,
    }
    headers = {
    'Content-Type': 'application/json'
    }
    requests.post(review_hook_url,headers = headers,data = json.dumps(bearychat_msg))

@engine.after_save('Alert')  # Alert 为需要 hook 的 class 的名称
def after_alert_save(alert):
    try:
        msg = alert.get('msg')
        alarming_bearychat(msg)
    except leancloud.LeanCloudError:
        raise leancloud.LeanEngineError(message='An error occurred while trying to save the Alert. ')

@engine.after_save('ReviewAlert')  # Alert 为需要 hook 的 class 的名称
def after_alert_save(alert):
    try:
        review_alarming_bearychat()
    except leancloud.LeanCloudError:
        raise leancloud.LeanEngineError(message='An error occurred while trying to save the Alert. ')
    # try:
    #     msg = alert.get('msg')
    #     review_alarming_bearychat(msg)
    # except leancloud.LeanCloudError:
    #     raise leancloud.LeanEngineError(message='An error occurred while trying to save the Alert. ')
