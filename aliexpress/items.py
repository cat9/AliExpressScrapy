# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AliexpressItem(scrapy.Item):
    # define the fields for your item here like:
    id = scrapy.Field()
    category = scrapy.Field()
    title = scrapy.Field()
    score = scrapy.Field()
    salesCount = scrapy.Field()
    price = scrapy.Field()
    property = scrapy.Field()
    img_urls = scrapy.Field()
    url = scrapy.Field()
