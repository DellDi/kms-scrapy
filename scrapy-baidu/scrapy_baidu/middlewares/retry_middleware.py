import logging
import time
from typing import Optional, Type
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from twisted.internet import defer
from twisted.internet.error import TimeoutError, DNSLookupError, ConnectionRefusedError
from twisted.web._newclient import ResponseNeverReceived
from scrapy.core.downloader.handlers.http11 import TunnelError

# 配置模块日志记录器
logger = logging.getLogger(__name__)

class CustomRetryMiddleware(RetryMiddleware):
    """自定义重试中间件，提供高级重试机制"""

    # 需要重试的异常类型
    EXCEPTIONS_TO_RETRY = (
        defer.TimeoutError,
        TimeoutError,
        DNSLookupError,
        ConnectionRefusedError,
        ResponseNeverReceived,
        TunnelError,
        IOError,
    )

    def __init__(self, settings):
        super().__init__(settings)
        # 基本重试配置
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429]))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST', -1)

        # 高级重试配置
        self.retry_delay = settings.getfloat('RETRY_DELAY', 1.0)
        self.exponential_backoff = settings.getbool('RETRY_EXPONENTIAL_BACKOFF', True)
        self.max_delay = settings.getfloat('RETRY_MAX_DELAY', 60.0)

        # 统计信息
        self.retry_stats = {
            'total_retries': 0,
            'success_retries': 0,
            'failed_retries': 0,
            'status_retries': {},
            'exception_retries': {},
        }

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建中间件实例"""
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        """爬虫启动时的处理"""
        logger.info("初始化重试中间件")
        self.reset_stats()

    def spider_closed(self, spider):
        """爬虫关闭时的处理"""
        logger.info("重试中间件统计信息:")
        logger.info("- 总重试次数: %d", self.retry_stats['total_retries'])
        logger.info("- 成功重试: %d", self.retry_stats['success_retries'])
        logger.info("- 失败重试: %d", self.retry_stats['failed_retries'])

        if self.retry_stats['status_retries']:
            logger.info("HTTP状态码重试统计:")
            for status, count in self.retry_stats['status_retries'].items():
                logger.info("  - %s: %d次", status, count)

        if self.retry_stats['exception_retries']:
            logger.info("异常重试统计:")
            for exc_name, count in self.retry_stats['exception_retries'].items():
                logger.info("  - %s: %d次", exc_name, count)

    def reset_stats(self):
        """重置统计信息"""
        self.retry_stats = {
            'total_retries': 0,
            'success_retries': 0,
            'failed_retries': 0,
            'status_retries': {},
            'exception_retries': {},
        }

    def _calculate_delay(self, retry_times: int) -> float:
        """计算重试延迟时间"""
        if self.exponential_backoff:
            delay = self.retry_delay * (2 ** (retry_times - 1))
            return min(delay, self.max_delay)
        return self.retry_delay

    def _get_retry_request(self, request, reason, spider):
        """获取重试请求"""
        retry_times = request.meta.get('retry_times', 0) + 1

        if retry_times <= self.max_retry_times:
            self.retry_stats['total_retries'] += 1

            # 创建新的请求
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retry_times
            retryreq.meta['retry_reason'] = reason
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust

            # 计算延迟时间
            delay = self._calculate_delay(retry_times)

            # 记录重试信息
            logger.info(
                "重试请求 %s (第 %d 次失败): %s | 延迟: %.2f秒",
                request, retry_times, reason, delay
            )

            # 应用延迟
            time.sleep(delay)

            return retryreq
        else:
            self.retry_stats['failed_retries'] += 1
            logger.error(
                "放弃重试 %s (已失败 %d 次): %s",
                request, retry_times, reason
            )
            return None

    def process_response(self, request, response, spider):
        """处理响应"""
        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            # 更新状态码统计
            status = str(response.status)
            self.retry_stats['status_retries'][status] = \
                self.retry_stats['status_retries'].get(status, 0) + 1

            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response

        # 检查自定义重试条件
        if self._should_retry(response):
            reason = 'custom_retry_condition'
            return self._retry(request, reason, spider) or response

        return response

    def process_exception(self, request, exception, spider):
        """处理异常"""
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY) and \
           not request.meta.get('dont_retry', False):
            # 更新异常统计
            exc_name = type(exception).__name__
            self.retry_stats['exception_retries'][exc_name] = \
                self.retry_stats['exception_retries'].get(exc_name, 0) + 1

            return self._retry(request, exception, spider)

    def _should_retry(self, response) -> bool:
        """自定义重试条件检查"""
        # 检查响应内容是否太短
        if len(response.body) < 100:
            logger.debug("响应内容过短，触发重试")
            return True

        # 检查是否包含错误关键词
        error_keywords = ['error', '异常', '请稍后重试']
        response_text = response.text.lower()
        if any(keyword in response_text for keyword in error_keywords):
            logger.debug("检测到错误关键词，触发重试")
            return True

        # 检查是否缺少关键内容
        if not response.css('#hotsearch-content-wrapper'):
            logger.debug("缺少关键内容，触发重试")
            return True

        return False

    def _retry(self, request, reason, spider):
        """执行重试"""
        retryreq = self._get_retry_request(request, reason, spider)
        if retryreq:
            self.retry_stats['success_retries'] += 1
            return retryreq
        return None