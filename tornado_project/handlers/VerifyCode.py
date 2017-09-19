# coding:utf-8
import logging
import re
import random
import datetime
import json
import base64
# import requests
import tornado.gen

from BaseHandler import BaseHandler
from utils.captcha.captcha import captcha
from constants import PIC_CODE_EXPIRES_SECONDS, SMS_CODE_EXPIRES_SECONDS
from utils.response_code import RET
# from libs.yuntongxun.SendTemplateSMS import ccp
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse
from hashlib import md5


class PicCodeHandler(BaseHandler):
    """处理图片验证码"""
    def get(self):
        pre_code_id = self.get_argument('pre', '')
        cur_code_id = self.get_argument('cur', '')
        name, text, image = captcha.generate_captcha()
        try:
            if pre_code_id:
                self.redis.delete('pic_code_%s' % pre_code_id)
            self.redis.setex('pic_code_%s' % cur_code_id, PIC_CODE_EXPIRES_SECONDS, text)
        except Exception as e:
            logging.error(e)
            self.wirte('')
        else:
            self.set_header('Content-Type', 'image/jpg')
            self.write(image)


class CreateRequest(object):
    """"""
    def __init__(self, to=17316198289, sms_code=10020033, expires=300, template_id=1):
        self.to = str(to)
        self.sms_code = str(sms_code)
        self.expires = expires
        self.templateId = str(template_id)
        self.appId = '8aaf07085df473bd015e0272f3b402a5'

    def get_request(self):
        # 构造请求体
        body = {
            "to": self.to,
            "appId": self.appId,
            "templateId": self.templateId,
            "datas": [str(self.sms_code), str(self.expires/60)]
        }
        body = json.dumps(body)
        c_length = len(body)

        # 构造请求网址
        account_sid = '8aaf07085df473bd015e0272f16f02a0'
        account_token = 'c3ded094c989472d9efaff994f64a669'
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        sig_parameter = account_sid + account_token + timestamp
        m = md5()
        m.update(sig_parameter)
        sig = m.hexdigest().upper()
        url = "https://app.cloopen.com:8883" +\
              "/2013-12-26/Accounts/" +\
              account_sid +\
              "/SMS/TemplateSMS?sig=" + sig

        # 构造请求头
        src = account_sid + ":" + timestamp
        auth = base64.encodestring(src).strip()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": auth,
            "content-length": c_length
        }
        return HTTPRequest(url, method='POST', headers=headers, body=body)


class PhoneCodeHandler(BaseHandler):
    """异步接口"""
    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        # 获取参数 pic_code_id, pic_code, mobile
        pic_code_id = self.json_args.get('pic_code_id')

        pic_code = self.json_args.get('pic_code')
        mobile = self.json_args.get('mobile')
        print mobile
        # 验证参数是否合格
        if not all((pic_code_id, pic_code, mobile)):
            self.write(dict(err_no=RET.PARAMERR, err_msg='参数缺失'))
            raise tornado.gen.Return()
        if not re.match(r'^1\d{10}$', mobile):
            self.write(dict(err_no=RET.PARAMERR, err_msg='手机号格式错误'))
            raise tornado.gen.Return()

        # 验证pic_code 是否通过
        try:
            real_pic_code = self.redis.get('pic_code_%s' % pic_code_id)
        except Exception as e:
            logging.error(e)
            self.write(dict(err_no=RET.DBERR, err_msg='数据库错误!'))
            raise tornado.gen.Return()
        if not real_pic_code:
            self.write((dict(err_no=RET.NODATA, err_msg='验证码过期!')))
            raise tornado.gen.Return()

        # 删除图片验证码
        try:
            self.redis.delete('pic_code_%s' % pic_code_id)
        except Exception as e:
            logging.error(e)

        if real_pic_code.lower() != pic_code.lower():
            self.write((dict(err_no=RET.DATAERR, err_msg='验证码错误!')))
            raise tornado.gen.Return()

        # 验证手机号是否存在
        sql = "SELECT count(*) counts FROM ih_user_profile WHERE up_mobile=%s "
        try:
            ret = self.db.get(sql, mobile)
        except Exception as e:
            logging.error(e)
            self.write((dict(err_no=RET.DBAERR, err_msg='数据库出错!')))
            raise tornado.gen.Return()
        else:
            if 0 != ret['counts']:
                self.write((dict(err_no=RET.DATAEXIST, err_msg='手机号已经注册!')))
                raise tornado.gen.Return()

        # 通过: 生成,储存并发送验证吗, 并返回前端
        sms_code = '%06d' % random.randint(1, 1000000)
        # 保存验证码
        try:
            self.redis.setex('sms_code_%s' % mobile, sms_code, SMS_CODE_EXPIRES_SECONDS)
        except Exception as e:
            logging.error(e)
            self.write(dict(err_no=RET.DBERR, err_msg='数据库出错'))
            raise tornado.gen.Return()

        # 发送验证码
        try:
            request_to = CreateRequest(to=mobile, sms_code=sms_code, expires=SMS_CODE_EXPIRES_SECONDS,template_id=1).get_request()
            rep = yield self.send_sms(request_to)
        except Exception as e:
            logging.error(e)
            self.write((dict(err_no=RET.THIRDERR, err_msg='发送短信失败!')))
            raise tornado.gen.Return()  # 此处需要注意
        # print rep[u"statusCode"] == "000000"

        if rep[u"statusCode"] == "000000":
            self.write((dict(err_no=RET.OK, err_msg='发送成功!')))
            raise tornado.gen.Return()  # 此处需要注意
        else:
            self.write((dict(err_no=RET.UNKOWNERR, err_msg='发送失败!')))
            raise tornado.gen.Return()

    @staticmethod
    @tornado.gen.coroutine
    def send_sms(request_to):
        http = AsyncHTTPClient()
        response = yield http.fetch(request_to)
        if response.error:
            rep = {"ret": 0}
        else:
            rep = json.loads(response.body)
        raise tornado.gen.Return(rep)
    # @tornado.gen.coroutine
    # def get(self):
    #     rep = yield self.get_ip_info("14.130.112.24")
    #     if 1 == rep["ret"]:
    #         self.write(u"国家：%s 省份: %s 城市: %s" % (rep["country"], rep["province"], rep["city"]))
    #     else:
    #         self.write("查询IP信息错误")
    #
    # @tornado.gen.coroutine
    # def get_ip_info(self, ip):
    #     http = tornado.httpclient.AsyncHTTPClient()
    #     response = yield http.fetch("http://int.dpool.sina.com.cn/iplookup/iplookup.php?format=json&ip=" + ip)
    #     if response.error:
    #         rep = {"ret:0"}
    #     else:
    #         rep = json.loads(response.body)
    #     raise tornado.gen.Return(rep)  # 此处需要注意
#
# class PhoneCodeHandler(BaseHandler):
#
#     def post(self, *args, **kwargs):
#         # 获取参数 pic_code_id, pic_code, mobile
#         pic_code_id = self.json_args.get('pic_code_id')
#
#         pic_code = self.json_args.get('pic_code')
#         mobile = self.json_args.get('mobile')
#         print mobile
#         # 验证参数是否合格
#         if not all((pic_code_id, pic_code, mobile)):
#             return self.write(dict(err_no=RET.PARAMERR, err_msg='参数缺失'))
#         if not re.match(r'^1\d{10}$', mobile):
#             return self.write(dict(err_no=RET.PARAMERR, err_msg='手机号格式错误'))
#
#         # 验证pic_code 是否通过
#         try:
#             real_pic_code = self.redis.get('pic_code_%s' % pic_code_id)
#         except Exception as e:
#             logging.error(e)
#             return self.write(dict(err_no=RET.DBERR, err_msg='数据库错误!'))
#         if not real_pic_code:
#             return self.write((dict(err_no=RET.NODATA, err_msg='验证码过期!')))
#
#         # 删除图片验证码
#         try:
#             self.redis.delete('pic_code_%s' % pic_code_id)
#         except Exception as e:
#             logging.error(e)
#
#         if real_pic_code.lower() != pic_code.lower():
#             return self.write((dict(err_no=RET.DATAERR, err_msg='验证码错误!')))
#
#         # 验证手机号是否存在
#         sql = "SELECT count(*) counts FROM ih_user_profile WHERE up_mobile=%s "
#         try:
#             ret = self.db.get(sql, mobile)
#         except Exception as e:
#             logging.error(e)
#             return self.write((dict(err_no=RET.DBAERR, err_msg='数据库出错!')))
#         else:
#             if 0 != ret['counts']:
#                 return self.write((dict(err_no=RET.DATAEXIST, err_msg='手机号已经注册!')))
#
#         # 通过: 生成并发送验证吗, 并返回前端
#         sms_code = '%06d' % random.randint(1, 1000000)
#         try:
#             print('----------------------1------------------')
#             ret = ccp.sendTemplateSMS(mobile, [sms_code, SMS_CODE_EXPIRES_SECONDS/60], 1)
#             print('----------------------2------------------')
#         except Exception as e:
#             logging.error(e)
#             return self.write((dict(err_no=RET.THIRDERR, err_msg='发送短信失败!')))
#         if ret:
#             return self.write((dict(err_no=RET.OK, err_msg='发送成功!')))
#         else:
#             return self.write((dict(err_no=RET.UNKOWNERR, err_msg='发送失败!')))

