# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import sqlite3
import threading

class AliexpressPipeline(object):
    collection_name = 'scrapy_items'
    SQL_TABLE = "create table if not exists product(id integer primary key,category TEXT,title TEXT, score varchar(128), salesCount varchar(128), price varchar(128),property TEXT,img_urls TEXT,url TEXT)"
    SQL_CHECK = "select count(id) from product where id =?"
    SQL_INSERT = "insert into product(id,category,title,score,salesCount,price,property,img_urls,url) values (?,?,?,?,?,?,?,?,?)"
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
                                                      item['salesCount'], item['price'], item['property'],
                                                      item['img_urls'], item['url']))
                self.connect.commit()

                self.total = self.total+1
                self.thread_lock.release()
                print('current size:%d' % self.total)
            else:
                print("find ,ignore it: %s" % (item['id']))
        except Exception as e:
            print(e)
        return item

    def check_exist_by_url(self, url):
        self.thread_lock.acquire()
        q_url = url.split('?')[0]
        self.cursor.execute(self.SQL_CHECK_BY_URL, (q_url,))
        count = self.cursor.fetchone()[0]
        self.thread_lock.release()
        return count > 0
