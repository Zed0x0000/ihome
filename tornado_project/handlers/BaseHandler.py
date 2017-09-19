# coding:utf-8
import json
import logging

from tornado.web import RequestHandler
from utils.session import Session


class BaseHandler(RequestHandler):
    """Handler基类"""
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        # self.db = self.application.db
        # self.redis = self.application.redis
        self.json_args = {}
        self.session = {}
        # self.session = Session(self)

    # @property
    # def session(self):
    #     return Session(self)

    @property
    def db(self):
        return self.application.db

    @property
    def redis(self):
        return self.application.redis

    def set_default_headers(self):
        """设置默认json格式"""
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def initialize(self):
        pass

    def prepare(self):
        """预解析JSON数据"""
        self.xsrf_token
        if self.request.headers.get('Content-Type', '').startswith('application/json'):
            self.json_args = json.loads(self.request.body)

    def write_error(self, status_code, **kwargs):
        pass

    def on_finish(self):
        pass

    def get_current_user(self):
        try:
            self.session = Session(self)
        except Exception as e:
            logging.error(e)
            return {}
        else:
            return self.session.data
