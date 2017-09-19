# coding:utf-8
import logging
import json
import constants
import config
import os
import datetime

from .BaseHandler import BaseHandler
from utils.response_code import RET
from utils.commons import required_login
from utils.SaveImage import SaveImage

class AreaInfoHandler(BaseHandler):
    """区域信息接口"""
    def get(self, *args, **kwargs):
        # 先去redis缓存中查找
        try:
            ret = self.redis.get('area_info')
        except Exception as e:
            logging.error(e)
            ret = None
        # 如果找到,返回,ret为字符串json格式的
        if ret:
            # resp = '{"errcode":"0", "errmsg":"OK", "data":%s}' % ret
            # return self.write(resp)
            logging.info('hit in redis')
            return self.write('{"errcode": "0", "errmsg": "ok", "data": %s}' % ret)

        # 如果没有在redis中找到继续去数据库中找
        try:
            sql = "select ai_area_id, ai_name from ih_area_info "
            ret = self.db.query(sql)  # ret为列表形式的,列表里面是类字典对象
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="查询数据库出错"))
        if not ret:
            return self.write(dict(errcode=RET.NODATA, errmsg="没有数据"))
        # 讲查找结果遍历
        data = []
        for i in ret:
            area_info_dict = {
                'area_id': i.ai_area_id,
                'name': i.ai_name
            }
            data.append(area_info_dict)
        # 将数据序列化,并存入redis中去
        data_str = json.dumps(data)
        try:
            self.redis.setex('area_info', constants.REDIS_AREA_INFO_EXPIRES_SECONDS, data_str)
        except Exception as e:
            logging.error(e)

        # 返回给前段内容
        self.write(dict(errcode=RET.OK, errmsg="ok", data=data))


class MyHouseHandler(BaseHandler):
    """我的房屋信息"""
    @required_login
    def get(self, *args, **kwargs):
        """获取房屋信息"""
        user_id = self.session.data['user_id']
        # 查询我的房屋信息
        try:
            sql = "select hi_house_id,hi_title,hi_price,hi_ctime,b.ai_name,hi_index_image_url " \
                  "from ih_house_info a left join ih_area_info b " \
                  "on a.hi_area_id=b.ai_area_id " \
                  "where a.hi_user_id=%s " \
                  "order by a.hi_house_id desc;"

            houses = self.db.query(sql, user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg='查询数据库出错'))
        if not houses:
            houses = []

        # 遍历构造房屋信息字典的列表
        out_houses = []
        for house_row in houses:
            house = {
                'house_id': house_row['hi_house_id'],
                'title': house_row['hi_title'],
                'price': int(house_row['hi_price']),
                'ctime': house_row['hi_ctime'].strftime('%Y-%m-%d'),
                'area_name': house_row['ai_name'],
                'img_url': os.path.join(config.static_back_path, house_row['hi_index_image_url'])
                if house_row['hi_index_image_url'] else ''
            }
            out_houses.append(house)
        self.write(dict(errcode=RET.OK, errmsg='ok', houses=out_houses))


class HouseInfoHandler(BaseHandler):
    """房屋信息,保存与展现"""

    @required_login
    def post(self, *args, **kwargs):
        """保存"""
        # 获取参数
        """{
            "title":"",
            "price":"",
            "area_id":"1",
            "address":"",
            "room_count":"",
            "acreage":"",
            "unit":"",
            "capacity":"",
            "beds":"",
            "deposit":"",
            "min_days":"",
            "max_days":"",
            "facility":["7","8"]
        }"""
        # user_id = self.get_argument('uid')
        user_id = self.session.data['user_id']
        title = self.json_args.get('title')
        price = self.json_args.get('price')
        area_id = self.json_args.get('area_id')
        address = self.json_args.get('address')
        room_count = self.json_args.get('room_count')
        acreage = self.json_args.get('acreage')
        unit = self.json_args.get('unit')
        capacity = self.json_args.get('capacity')
        beds = self.json_args.get('beds')
        deposit = self.json_args.get('deposit')
        min_days = self.json_args.get('min_days')
        max_days = self.json_args.get('max_days')
        facility = self.json_args.get('facility')

        # 检验参数的合法性
        if not all((
                    user_id, title, price, area_id, address, room_count, acreage,
                    unit, capacity, beds, deposit, min_days, max_days, facility
                    )):
            return self.write(dict(errcode=RET.PARAMERR, errmsg='参数缺失'))
        try:
            price = int(price)*100
            deposit = int(deposit)*100
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.OK, errmsg='参数错误'))
        # 数据库操作 (房屋信息, 设备信息)

        try:
            sql = "insert into ih_house_info(hi_user_id,hi_title,hi_price,hi_area_id,hi_address,hi_room_count," \
                  "hi_acreage,hi_house_unit,hi_capacity,hi_beds,hi_deposit,hi_min_days,hi_max_days) " \
                  "values(%(user_id)s,%(title)s,%(price)s,%(area_id)s,%(address)s,%(room_count)s,%(acreage)s," \
                  "%(house_unit)s,%(capacity)s,%(beds)s,%(deposit)s,%(min_days)s,%(max_days)s)"
            # 对于insert语句，execute方法会返回最后一个自增id
            house_id = self.db.execute(sql, user_id=user_id, title=title, price=price, area_id=area_id, address=address,
                                       room_count=room_count, acreage=acreage, house_unit=unit, capacity=capacity,
                                       beds=beds, deposit=deposit, min_days=min_days, max_days=max_days)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg='数据库出错'))

        try:
            sql = "insert into ih_house_facility(hf_house_id, hf_facility_id) values"
            sql_values = []
            values = []
            for f in facility:
                sql_values.append('(%s, %s)')
                values.append(house_id)
                values.append(f)
            sql += ','.join(sql_values)
            self.db.execute(sql, *values)
        except Exception as e:
            logging.error(e)
            # 如果存入设施表失败,得把房屋信息表给删掉
            try:
                self.db.execute("delete from ih_house_info where hi_house_id=%s", house_id)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.DBERR, errmsg='删除数据库失败'))
            else:
                return self.write(dict(errcode=RET.DBERR, errmsg='数据库保存出错'))
        self.write(dict(errcode=RET.OK, errmsg='ok', house_id=house_id))


class HouseImageHandler(BaseHandler):
    """房屋照片"""
    @required_login
    def post(self):
        # user_id = self.session.data["user_id"]
        house_id = self.get_argument("house_id")
        house_image_body = self.request.files["house_image"][0]["body"]
        house_image_name = self.request.files["house_image"][0]["filename"]
        # 调用我们封装好的SaveImage方法保存图片
        try:
            print('测试-'*10)
            print config.upload_path
            print('测试-'*10)
            save_image = SaveImage(house_image_body, config.upload_path, self.db, house_image_name)
            img_name = save_image.save()
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.THIRDERR, "errmsg": "saveImage error"})

        if not img_name:
            return self.write({"errcode": RET.THIRDERR, "errmsg": "saveImage error"})
        try:
            # 保存图片路径到数据库ih_house_image表,并且设置房屋的主图片(ih_house_info中的hi_index_image_url）
            # 我们将用户上传的第一张图片作为房屋的主图片
            sql = "insert into ih_house_image(hi_house_id,hi_url) values(%s,%s);" \
                  "update ih_house_info set hi_index_image_url=%s " \
                  "where hi_house_id=%s and hi_index_image_url is null;"
            self.db.execute(sql, house_id, img_name, img_name, house_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "upload failed"})
        img_url = os.path.join(config.static_back_path, img_name)
        self.write({"errcode": RET.OK, "errmsg": "OK", "url": img_url})











