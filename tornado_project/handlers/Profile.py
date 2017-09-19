# coding:utf-8
import logging
import constants

from .BaseHandler import BaseHandler
from utils.commons import required_login
from utils.response_code import RET
from utils.qiniu_storage import storage


class AvatarHandler(BaseHandler):
    """上传头像, 七牛sdk版本"""
    @required_login
    def post(self):
        files = self.request.files.get("avatar")
        if not files:
            return self.write(dict(errcode=RET.PARAMERR, errmsg="未传图片"))
        avatar = files[0]["body"]
        # 调用七牛上传图片
        try:
            file_name = storage(avatar)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.THIRDERR, errmsg="上传失败"))

        # 从session数据中取出user_id
        user_id = self.session.data["user_id"]

        # 保存图片名（即图片url）到数据中
        sql = "update ih_user_profile set up_avatar=%(avatar)s where up_user_id=%(user_id)s"
        try:
            row_count = self.db.execute_rowcount(sql, avatar=file_name, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="保存错误"))
        self.write(dict(errcode=RET.OK, errmsg="保存成功", data="%s%s" % (constants.QINIU_URL_PREFIX, file_name)))

class ProfileHandler(BaseHandler):
    """个人信息"""
    @required_login
    def get(self):
        user_id = self.session.data['user_id']
        try:
            ret = self.db.get("select up_name,up_mobile,up_avatar from ih_user_profile where up_user_id=%s", user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg":"get data error"})
        if ret["up_avatar"]:
            img_url = constants.QINIU_URL_PREFIX + ret["up_avatar"]
        else:
            img_url = None
        self.write({"errcode": RET.OK, "errmsg": "OK",
                    "data": {"user_id": user_id, "name": ret["up_name"], "mobile": ret["up_mobile"], "avatar": img_url}})


class NameHandler(BaseHandler):
    """名字处理"""
    @required_login  # 装饰器中已经讲session创建出来了
    def post(self):
        # 获取参数
        user_id = self.session.data['user_id']
        modify_name = self.json_args.get('name')

        # 判断传入参数的合法性
        modify_name = modify_name.strip()
        if modify_name in (None, '') or len(modify_name.encode('utf-8')) < 5:
            return self.write(dict(errcode=RET.PARAMERR, errmsg='参数不合格'))

        # 写入数据库更改,利用字段的唯一性,判断是否重名
        try:
            sql = "update ih_user_profile set up_name=%(name)s where up_user_id=%(user_id)s;"
            self.db.execute_rowcount(sql, name=modify_name, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DATAEXIST, errmsg='用户名已经存在!'))

        # 保存session更改name
        self.session.data['name'] = modify_name
        try:
            self.session.save()
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg='数据库出错'))
        self.write(dict(errcode=RET.OK, errmsg='ok', data={'name': modify_name}))


class AuthHandler(BaseHandler):
    """身份认证"""
    @required_login
    def get(self):
        user_id = self.session.data['user_id']
        # 根据user_id来查询身份证信息
        try:
            sql = "select up_real_name, up_id_card from ih_user_profile where up_user_id=%s;"
            ret = self.db.get(sql, user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="查询数据库出错"))
        real_name, id_card = ret.up_real_name, ret.up_id_card
        self.write(dict(errcode=RET.OK, errmsg="ok", data={'real_name': real_name, 'id_card': id_card}))

    @required_login
    def post(self, *args, **kwargs):
        # 获取参数
        real_name = self.json_args.get('real_name')
        id_card = self.json_args.get('id_card')
        user_id = self.session.data['user_id']
        print('1'*30)
        print real_name, id_card
        # 判断参数的有效性
        if not all((real_name, id_card)):
            return self.write(dict(errcode=RET.PARAMERR, errmsg='参数缺失'))

        # 调用接口查询身份证信息的有效性

        # 存入数据库
        try:
            sql = "update ih_user_profile set up_real_name=%(real_name)s, up_id_card=%(id_card)s where up_user_id=%(user_id)s;"
            self.db.execute_rowcount(sql, real_name=real_name, id_card=id_card, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg='数据库操作出错'))
        self.write(dict(errcode=RET.OK, errmsg='ok'))



