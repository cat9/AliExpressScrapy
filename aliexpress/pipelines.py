# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import scrapy
import sqlite3
import threading
import os
import shutil
import re
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

# item['id'], item['category'], item['title'], item['score'],
# item['salesCount'], item['price'], item['property'],
# item['img_urls'], item['url']

class AliexpressImagesPipeline(ImagesPipeline):
    current_dir = ''
    def __init__(self, store_uri, download_func=None, settings=None):
        super().__init__(store_uri, download_func, settings)
        self.current_dir=os.getcwd()+r'\images'

    def get_media_requests(self, item, info):
        if item['img_urls']:
            images = item['img_urls'].split(' || ')
            for image in images:
                yield scrapy.Request(image, priority=15)

    def item_completed(self, results, item, info):
        image_paths = [x['path'] for ok, x in results if ok]
        image_urls = [x['url'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem("Item contains no images")

        category = re.sub(r'[>\s\']', '_', item['category'])

        item_dir = os.path.join(self.current_dir, category, item['id'])
        try:
            os.makedirs(item_dir)
        except Exception as err:
            print(err)

        for image in image_paths:
            image_path = os.path.join(self.store.basedir, image.replace('/', '\\'))
            move_to = os.path.join(item_dir, os.path.basename(image_path))
            shutil.move(image_path, move_to)

        return item

class AliexpressPipeline(object):
    collection_name = 'scrapy_items'
    SQL_TABLE = "create table if not exists product(id integer primary key,category TEXT,title TEXT, score varchar(128), salesCount varchar(128), price varchar(128),skus TEXT,property TEXT,img_urls TEXT,url TEXT)"
    SQL_CHECK = "select count(id) from product where id =?"
    SQL_INSERT = "insert into product(id,category,title,score,salesCount,price,skus,property,img_urls,url) values (?,?,?,?,?,?,?,?,?,?)"
    SQL_CHECK_NUM = "select count(id) from product"
    SQL_CHECK_BY_URL = "select count(id) from product where url =?"
    connect = None
    cursor = None
    total = 0
    thread_lock = threading.Lock()

    def __init__(self, db_name):
        self.db_name = db_name

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_name=crawler.settings.get('DB_NAME', "default.db"),
        )

    def open_spider(self, spider):
        conn = sqlite3.connect(self.db_name)
        conn.execute(self.SQL_TABLE)
        conn.commit()
        self.cursor = conn.cursor()
        self.connect = conn
        self.cursor.execute(self.SQL_CHECK_NUM)
        self.total = self.cursor.fetchone()[0]
        print('current size:%d' % self.total)
        spider.set_db_pipeline(self)

    def close_spider(self, spider):
        if self.cursor:
            self.cursor.close()
        self.connect.close()

    def process_item(self, item, spider):
        try:
            self.thread_lock.acquire()
            self.cursor.execute(self.SQL_CHECK, (item['id'],))
            if int(self.cursor.fetchone()[0]) == 0:
                print("not find ,insert it: %s" % (item['id']))
                self.cursor.execute(self.SQL_INSERT, (item['id'], item['category'], item['title'], item['score'],
                                                      item['salesCount'], item['price'], item['skus'], item['property'],
                                                      item['img_urls'], item['url']))
                self.connect.commit()
                self.total = self.total+1
                print('current size:%d' % self.total)
            else:
                print("find ,ignore it: %s" % (item['id']))
        except Exception as e:
            print(e)
        finally:
            self.thread_lock.release()
        return item

    def check_exist_by_url(self, url):
        self.thread_lock.acquire()
        q_url = url.split('?')[0]
        self.cursor.execute(self.SQL_CHECK_BY_URL, (q_url,))
        count = self.cursor.fetchone()[0]
        self.thread_lock.release()
        return count > 0
