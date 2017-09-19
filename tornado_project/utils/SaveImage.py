# coding:utf-8
import os
import torndb
import config
import logging

from hashlib import sha1


def singleton(cls):
    """单例模式装饰器"""
    instance = []

    def wrapper(*args, **kwargs):
        if not instance:
            instance[0] = cls(*args, **kwargs)
        return instance[0]
    return wrapper


class SaveImage(object):
    """
    传入参数:
    data: 文件二进制打开的内容;
    path: 文件保存的路径
    file_name: 文件原有名称

    操作内容:
     1. 用sha1哈希后的值作为图片的新名称
     2. 将hash后的值及path拼接,查询数据库是否相同(sql:hash_file)
        a. 不同,将hash与path的值存入数据库中,并将文件保存值指定路径,执行b
        b. 相同,:return: 返回hash值及路径

    :return: 返回图片的新名称new_name(含文件格式)
    """
    _create_table_status = None

    def __init__(self, data, path, db_connected, file_name='.jpg'):
        self.db = db_connected
        # self.db = torndb.Connection(**config.mysql_option)
        self.create_table()
        self.data = data
        self.path = path
        self.file_name = file_name
        self.file_format = self.get_file_format()

    def _create_table(self):
        """如果表不存在,创建表"""
        sql = "create table if not exists hash_file(" \
              "id bigint primary key not null auto_increment," \
              "hf_path varchar(128) not null," \
              "hf_hash_val char(40) not null," \
              "UNIQUE `uk_path_val` (hf_path, hf_hash_val)" \
              ")ENGINE=InnoDB auto_increment=10000 DEFAULT CHARSET=utf8 COMMENT='哈希文件表';"
        try:
            self.db.execute(sql)
        except Exception as e:
            logging.error(e)
            raise e

    def create_table(self):
        """如果是第一次调用,则调用一次_create_table,否则不掉用"""
        if not SaveImage._create_table_status:
            SaveImage._create_table_status = True
            self._create_table()

    def get_file_format(self):
        """得到文件的后缀名"""
        index = self.file_name.rfind('.')
        if -1 == index:
            file_format = ''
            return file_format
        file_format = self.file_name[index:]  # 含有'.'
        print file_format
        return file_format

    def save(self):

        # hash
        try:
            s = sha1()
            s.update(self.data)
            hash_val = s.hexdigest()
            hash_name = hash_val + self.file_format
            print hash_name
            print('1'*30)

            # 保存数据库,利用数据库两列数据的唯一性约束判断是否有相同的hash_name(相同的文件)
            try:
                sql = "insert into hash_file(hf_path, hf_hash_val) values(%s,%s);"
                self.db.execute(sql, self.path, hash_val)  # 得到自增id
            except Exception as e:
                logging.error(e)
                # 有相同的文件, 返回hash_name
                print('2'*30)
                return hash_name
            # 不同的文件,成功存入数据库,并保存在本地
            with open(os.path.join(self.path, hash_name), 'wb') as f:
                f.write(self.data)
            print('3'*30)
            return hash_name
        except Exception as e:
            logging.error(e)
            raise e



if __name__ == '__main__':
    # up_file = raw_input('请输入你要上传文件: ')
    up_file = '/home/python/Desktop/tornado1/tornado_project/static/home03.jpg'
    with open(up_file, 'rb') as f:
        data_in = f.read()
        f.close()
        print type(data_in)
        save_file = SaveImage(data_in, config.upload_path)
        save_file.save()




