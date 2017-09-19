# coding:utf-8
import os


# application配置参数
settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'template'),
    'cookie_secret': 'S1k6dGTZRNq0bfpl3O2Y11o9cfFSaUDOlv0+gg0USgE=',
    'xsrf_cookies': True,
    'debug': True,

}

# 数据库配置参数
mysql_option = dict(
    host='127.0.0.1',
    database='ihome',
    user='root',
    password='mysql',

)

redis_option = dict(
    host='127.0.01',
    port=6379,

)

# 日志文件配置
log_file = os.path.join(os.path.dirname(__file__), 'logs/log')
log_level = 'debug'

# 上传文件保存路径
static_back_path = os.path.join('/static', 'uploadFiles')
upload_path = os.path.join(os.path.dirname(__file__), 'static/uploadFiles')


