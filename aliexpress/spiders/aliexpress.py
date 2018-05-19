# -*- coding: utf-8 -*-
import scrapy
from selenium import webdriver
import time
import json
from aliexpress.items import AliexpressItem
import re
from urllib import parse as urlparse


class AliExpressSpider(scrapy.Spider):
    name = 'aliexpress'
    allowed_domains = ['aliexpress.com']
    start_urls = ['https://www.aliexpress.com/all-wholesale-products.html']
    my_cookies = {}
    debug = False
    _db_pipeline = None
    max_page_count = 10

    def set_db_pipeline(self, pipeline):
        self._db_pipeline = pipeline

    def start_requests(self):
        self._wait_for_login()
        self.debug = self.settings.getbool("IS_DEBUG", False)
        self.max_page_count = self.settings.getint("MAX_PAGE_COUNT", 10)
        print("start_requests")
        for url in self.start_urls:
            yield scrapy.Request(url, cookies=self.my_cookies)

    def parse(self, response):
        print("AliExpressSpider parse")
        if response.status == 302:
            request = scrapy.Request(response.url)
            request.dont_filter = True
            request.meta['redirect_times'] = self.settings.getint('REDIRECT_MAX_TIMES')
            print("TestSpider parse redirects %s", response.url)
            yield request
        else:
            items = response.xpath(
                "//div[@class='sub-item-cont-wrapper']/ul[contains(@class,'sub-item-cont')]/li/a/@href")
            if self.debug:
                items = items[:2]
            for item in items:
                url = item.extract()
                if url.startswith("//"):
                    url = "https:" + url
                yield scrapy.Request(url, callback=self.parse_single_page, priority=1)

    def parse_single_page(self, response):
        print("AliExpressSpider parse_single_page")
        if response.status == 302:
            request = scrapy.Request(response.url, callback=self.parse_single_page, priority=1)
            request.dont_filter = True
            request.meta['redirect_times'] = self.settings.getint('REDIRECT_MAX_TIMES')
            print("TestSpider parse_single_page redirects %s" % response.url)
            yield request
        else:
            scripts_items = response.xpath("//script/text()")
            # extra_params = self._generate_extra_params(scripts_items)
            items = response.xpath(
                "//li[contains(@class,'list-item')]/div/div/div/h3/a/@href|//div[@class='item']/div[@class='info']/h3/a/@href")

            if self.debug:
                items = items[:2]
            for item in items:
                raw_url = item.extract()
                if raw_url.startswith("//"):
                    raw_url = "https:" + raw_url
                if self._db_pipeline and self._db_pipeline.check_exist_by_url(raw_url):
                    print('exist url ignore it:%s' % raw_url)
                    continue
                rq = scrapy.Request(raw_url, callback=self.parse_single_goods, priority=10)
                yield rq

            if not self.debug:
                response.xpath("//div[contains(@class,'ui-pagination-navi')]/a[contains(@class,'page-next')]")
                next = response.xpath("//a[contains(@class,'page-next')]/@href").extract()
                curPage = response.xpath("//span[@class='ui-pagination-active']/text()").extract()
                if len(next) == 1 and len(curPage) == 1 and int(curPage[0]) <= self.max_page_count:
                    url = next[0]
                    if url.startswith("//"):
                        url = "https:" + url
                    yield scrapy.Request(url, callback=self.parse_single_page, priority=9)

    def parse_single_goods(self, response):
        print("AliExpressSpider parse_single_goods")
        if response.status == 302:
            request = scrapy.Request(response.url, callback=self.parse_single_goods, priority=9)
            request.dont_filter = True
            request.meta['redirect_times'] = self.settings.getint('REDIRECT_MAX_TIMES')
            print("TestSpider parse_single_goods redirects %s", response.url)
            yield request
        else:
            item = AliexpressItem()
            item['id'] = self._pvalue(response, "//form[@name='buyNowForm']/input[@name='objectId']/@value")
            item['category'] = self._pvalue(response, "//div[@class='ui-breadcrumb']/div/descendant::a/text()", -1, '>')
            item['title'] = self._pvalue(response, "//div[@id='j-detail-page']/div/div/div/div/h1[@class='product-name']/text()")
            item['score'] = self._pvalue(response, "//div[@class='product-customer-reviews']/span[@class='percent-num']/text()")
            item['salesCount'] = self._pvalue(response, "//span[@id='j-order-num']/text()").split(" ")[0]
            prices = response.xpath(
                "//span[@id='j-sku-discount-price']/descendant-or-self::text()").extract()
            if len(prices) != 0:
                item['price'] = "".join(prices)
            else:
                prices = response.xpath(
                    "//span[@id='j-sku-price']/descendant-or-self::text()").extract()
                item['price'] = "".join(prices)
            properties_items = response.xpath(
                "//ul[contains(@class,'product-property-list')]/li[@class='property-item']")
            properties = []
            for prop_item in properties_items:
                item_texts = prop_item.xpath("span/text()").extract()
                if len(item_texts) == 2:
                    properties.append(item_texts[0] + item_texts[1])
            item['property'] = '||'.join(properties)
            images = response.xpath(
                "//ul[@id='j-image-thumb-list']//img/@src").extract()
            item['img_urls'] = self._values_to_string(images, " || ", lambda x: re.sub(r'_.*?\.jpg', "", x))
            item['url'] = response.url.split("?")[0]
            yield item

    def _generate_extra_params(self, scripts):
        ret=""
        for script in scripts:
            tmp = script.extract().strip()
            if tmp.startswith("with(document)"):
                text=re.search(r'dmtrack_c=\{(.*?)\}', tmp).group(1)
                text=urlparse.unquote(text)
                ws_ab_test=re.search(r'ws_ab_test=(.*?)\|', text).group(1)
                ret="ws_ab_test="+ws_ab_test
                algo_pvid=re.search(r'algo_pvid=(.*?)\|', text).group(1)
                ret = ret + "&algo_expid=" + algo_pvid
                ret = ret + "&algo_pvid=" + algo_pvid
                ret = ret + "&priceBeautifyAB=0"
                break
        return ret

    def _pvalue(self, response, path, index=0, slot=''):
        items = response.xpath(path).extract()
        size = len(items)
        if size > 0:
            if index < 0:
                return slot.join(items)
            else:
                return items[index]
        return ''

    def _generate_full_url(self,raw_url, extra_params):
        if '?' in raw_url:
            return raw_url+'&'+extra_params
        else:
            return raw_url+'?'+extra_params


    def _values_to_string(self, values, slot, fuc=None):
        vs = ""
        last_index = len(values) - 1
        for i, v in enumerate(values):
            if fuc:
                vs = vs + fuc(v)
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
            if self.settings.getint("WEB_DRIVE", 0) == 1:
                driver = webdriver.Firefox()
            else:
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
            # driver.close()
            with open("cookies.txt", "w") as f:
                json.dump(self.my_cookies, f)
