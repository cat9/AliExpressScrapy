# -*- coding: utf-8 -*-
import scrapy
from selenium import webdriver
import time
import json
from aliexpress.items import AliexpressItem
import re


class TestSpider(scrapy.Spider):
    name = 'test'
    allowed_domains = ['aliexpress.com']
    start_urls = ['https://www.aliexpress.com/all-wholesale-products.html']
    my_cookies = {}

    def start_requests(self):
        self._wait_for_login()
        print("start_requests")
        for url in self.start_urls:
            yield scrapy.Request(url, cookies=self.my_cookies)

    def parse(self, response):
        items = response.xpath("//div[@class='sub-item-cont-wrapper']/ul[contains(@class,'sub-item-cont')]/li/a/@href")
        for item in items[:2]:
            url = item.extract()
            if url.startswith("//"):
                url = "https:" + url
            yield scrapy.Request(url, callback=self.parse_single_page)

    def parse_single_page(self, response):
        items = response.xpath("//li[contains(@class,'list-item')]/div/div/div/h3/a/@href|//div[@class='item']/div[@class='info']/h3/a/@href")
        for item in items[:2]:
            url = item.extract()
            if url.startswith("//"):
                url = "https:" + url
            yield scrapy.Request(url,  callback=self.parse_single_goods)

        # response.xpath("//div[contains(@class,'ui-pagination-navi')]/a[contains(@class,'page-next')]")
        next=response.xpath("//a[contains(@class,'page-next')]/@href").extract()
        curPage=response.xpath("//span[@class='ui-pagination-active']/text()").extract()
        if len(next)==1 and len(curPage)==1 and int(curPage[0])<3:
            url = next[0]
            if url.startswith("//"):
                url = "https:" + url
            yield scrapy.Request(url,  callback=self.parse_single_page)


    def parse_single_goods(self, response):
        item = AliexpressItem()
        item['id'] = response.xpath(
            "//form[@name='buyNowForm']/input[@name='objectId']/@value").extract()[0]
        categories = response.xpath(
            "//div[@class='ui-breadcrumb']/div/descendant::a/text()").extract()
        item['category'] = ">".join(categories)
        item['title'] = response.xpath(
            "//div[@id='j-detail-page']/div/div/div/div/h1[@class='product-name']/text()").extract()[0]
        item['score'] = response.xpath(
            "//div[@class='product-customer-reviews']/span[@class='percent-num']/text()").extract()[0]
        item['salesCount'] = response.xpath(
            "//span[@id='j-order-num']/text()").extract()[0].split(" ")[0]
        prices = response.xpath(
            "//span[@id='j-sku-discount-price']/descendant-or-self::text()").extract()
        if len(prices)!=0:
            item['price']="".join(prices)
        else:
            prices = response.xpath(
                "//span[@id='j-sku-price']/descendant-or-self::text()").extract()
            item['price']="".join(prices)
        properties_items = response.xpath(
            "//ul[contains(@class,'product-property-list')]/li[@class='property-item']")
        properties=[]
        for prop_item in properties_items:
            item_texts=prop_item.xpath("span/text()").extract()
            if len(item_texts)==2:
                properties.append(item_texts[0]+item_texts[1])
        item['property']='||'.join(properties)
        images = response.xpath(
            "//ul[@id='j-image-thumb-list']//img/@src").extract()
        item['img_urls']=self._values_to_string(images, " || ", lambda x:re.sub(r'_.*?\.jpg', "", x))
        item['url'] = response.url.split("?")[0]

        # print(item)
        yield item

    def _values_to_string(self, values, slot,fuc=None):
        vs = ""
        last_index = len(values) - 1
        for i, v in enumerate(values):
            if fuc:
                vs=vs+fuc(v)
            else:
                vs = vs + v
            if i != last_index:
                vs = vs + slot
        return vs

    def _wait_for_login(self):
        try:
            with open("cookies.txt", "r") as f:
                self.my_cookies = json.loads(f.read())
        except Exception as e:
            print('Error:', e)

        if len(self.my_cookies) == 0:
            # driver = webdriver.Firefox()
            driver = webdriver.Chrome()
            driver.get("https://login.aliexpress.com")
            is_login = False
            while not is_login:
                print("wait for login")
                driver.implicitly_wait(4)
                time.sleep(4)
                source = driver.page_source
                if source and "My AliExpress" in source:
                    is_login = True
            self.my_cookies = driver.get_cookies()
            driver.close()
            with open("cookies.txt", "w") as f:
                json.dump(self.my_cookies, f)
