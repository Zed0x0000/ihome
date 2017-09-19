# coding=utf-8
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options
import torndb
import redis
import config


from tornado.options import options, define
from tornado.web import RequestHandler
from urls import handlers


define('port', default=8000, type=int, help='run server on the given port')


class Application(tornado.web.Application):

    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.db = torndb.Connection(
            **config.mysql_option
            # host='127.0.0.1',
            # database='ihome',
            # user='root',
            # password='mysql',

        )
        self.redis = redis.StrictRedis(
            **config.redis_option
            # host='127.0.01',
            # port=6379
        )


def main():
    options.logging = config.log_level
    options.log_file_prefix = config.log_file
    tornado.options.parse_command_line()

    app = Application(
        handlers, **config.settings
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)

    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
