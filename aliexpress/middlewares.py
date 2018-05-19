# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

import logging
from scrapy.contrib.downloadermiddleware.redirect import RedirectMiddleware
from scrapy.spidermiddlewares.httperror import HttpErrorMiddleware
from scrapy.spidermiddlewares.httperror import HttpError
from six.moves.urllib.parse import urljoin
from w3lib.url import safe_url_string
from scrapy.exceptions import IgnoreRequest

logger = logging.getLogger(__name__)


class AliexpressHttpErrorMiddleware(HttpErrorMiddleware):

    def process_spider_input(self, response, spider):
        if 200 <= response.status < 300:  # common case
            return
        meta = response.meta
        if 'handle_httpstatus_all' in meta:
            return
        if 'handle_httpstatus_list' in meta:
            allowed_statuses = meta['handle_httpstatus_list']
        elif self.handle_httpstatus_all:
            return
        else:
            allowed_statuses = getattr(spider, 'handle_httpstatus_list', self.handle_httpstatus_list)
        if response.status in allowed_statuses:
            return

        if response.status == 302:
            location = safe_url_string(response.headers['location'])
            if location.startswith('https://sec.aliexpress.com') or location.startswith('https://login.aliexpress.com'):
                return
        raise HttpError(response, 'Ignoring non-200 response')


class AliexpressRedirectMiddleware(RedirectMiddleware):

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest

        if (request.meta.get('dont_redirect', False) or
                response.status in getattr(spider, 'handle_httpstatus_list', []) or
                response.status in request.meta.get('handle_httpstatus_list', []) or
                request.meta.get('handle_httpstatus_all', False)):
            return response

        allowed_status = (301, 302, 303, 307, 308)
        if 'Location' not in response.headers or response.status not in allowed_status:
            return response

        location = safe_url_string(response.headers['location'])

        if response.status == 302 and (location.startswith('https://sec.aliexpress.com') or location.startswith('https://login.aliexpress.com')):
            redirects = request.meta.get('redirect_times', 0) + 1
            print("AliexpressRedirectMiddleware redirects %d,%s" % (redirects, location))
            if redirects <= self.max_redirect_times:
                return response
            else:
                logger.debug("Discarding %(request)s: max redirections reached",
                             {'request': request}, extra={'spider': spider})
                raise IgnoreRequest("max redirections reached")
        else:
            redirected_url = urljoin(request.url, location)

        if response.status in (301, 307, 308) or request.method == 'HEAD':
            redirected = request.replace(url=redirected_url)
            return self._redirect(redirected, request, spider, response.status)

        redirected = self._redirect_request_using_get(request, redirected_url)
        return self._redirect(redirected, request, spider, response.status)

