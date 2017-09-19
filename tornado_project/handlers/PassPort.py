# coding:utf-8
import logging
import re

from .BaseHandler import BaseHandler
from utils.response_code import RET
from hashlib import sha1
from utils.session import Session


class RegisterHandler(BaseHandler):
    """注册"""
    def post(self, *args, **kwargs):
        # 获取参数
        mobile = self.json_args.get('mobile')
        phone_code = self.json_args.get('phonecode')
        password = self.json_args.get('password')
        password2 = self.json_args.get('password2')
        print(mobile, phone_code, password, password2)
        # 参数是否合格
        if not all((mobile, phone_code, password, password2)):
            return self.write(dict(errcode=RET.PARAMERR, errmsg="参数缺失1"))
        if not re.match(r'^1\d{10}$', mobile):
            return self.write(dict(errcode=RET.PARAMERR, errmsg="手机号码格式错误"))
        if password != password2:
            return self.write(dict(errcode=RET.PARAMERR, errmsg="密码不一致1"))
        print('1'*30)

        # 判断验证码是否有效
        if '2468' != phone_code:

            try:
                real_phone_code = self.redis.get('sms_code_%s' % mobile)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.DBERR, errmsg='数据库出错'))
            if not real_phone_code:
                return self.write(dict(errcode=RET.DATAERR, errmsg='验证码已经过期'))
            if real_phone_code != phone_code:
                return self.write(dict(errcode=RET.DATAERR, errmsg='验证码错误!'))
            try:
                self.redis.delete('sms_code_%s' % mobile)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.DBERR, errmsg='数据库出错'))

        # 密码加密
        sha1_obj = sha1()
        sha1_obj.update(password)
        sha1_password = sha1_obj.hexdigest()
        print('2'*30)

        # 利用数据库手机号字段唯一性来验证手机号是否存在,并存储账户信息
        sql = "insert into ih_user_profile(up_name, up_mobile, up_passwd) values(%(name)s, %(mobile)s, %(passwd)s);"
        try:
            user_id = self.db.execute(sql, name=mobile, mobile=mobile, passwd=sha1_password)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DATAEXIST, errmsg='手机号已经存在'))

        # 制造session,保存已经登陆信息
        print('3'*30)
        try:
            session = Session(self)
            session.data['user_id'] = user_id
            session.data['mobile'] = mobile
            session.data['name'] = mobile
            print('4'*30)
            session.save()
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg='保存session,数据库出错'))

        self.write(dict(errcode=RET.OK, errmsg='注册成功!'))


class LoginHandler(BaseHandler):
    """登陆接口"""
    def post(self, *args, **kwargs):
        # 获取参数
        mobile = self.json_args.get('mobile')
        password = self.json_args.get('password')

        # 判断参数的合格性
        if not all((mobile, password)):
            return self.write(dict(errcode=RET.PARAMERR, errmsg='缺少参数'))
        if not re.match(r'^1\d{10}$', mobile):
            return self.write(dict(errcode=RET.PARAMERR, errmsg='手机号格式不正确'))

        # 查询数据库
        try:
            sql = "select up_user_id, up_name, up_passwd from ih_user_profile where up_mobile = %s;"
            res = self.db.get(sql, mobile)
        except Exception as e:
            logging.error(e)
            return self.write((dict(errcode=RET.DBERR, errmsg='数据库查询错误')))
        # 密码加密
        s1 = sha1()
        s1.update(password)
        password = s1.hexdigest()
        if res and res['up_passwd'] == unicode(password):
            # 设置session
            try:
                session = Session(self)
                session.data['user_id'] = res['up_user_id']
                session.data['name'] = res['up_name']
                session.data['mobile'] = mobile
                session.save()
            except Exception as e:
                logging.error(e)
                return self.write((dict(errcode=RET.DBERR, errmsg='数据库查询错误')))
            return self.write(dict(errcode=RET.OK, errmsg='登陆成功'))
        else:
            return self.write(dict(errcode=RET.DATAERR, errmsg='账号密码不正确'))


class CheckLoginHandler(BaseHandler):
    def get(self, *args, **kwargs):
        data = self.get_current_user()
        if data:
            return self.write(dict(errcode=RET.OK, errmsg='true', data={'name': data.get('name')}))
        else:
            return self.write(dict(errcode=RET.SESSIONERR, errmsg='false'))










