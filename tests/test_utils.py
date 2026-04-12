#!/usr/bin/env python3
"""
工具模块测试
"""

import pytest
import time
import threading

from src.utils.cache import MemoryCache, LRUCache, FunctionCache, cached
from src.utils.error_handler import (
    handle_errors, retry, safe_execute, FallDetectionError, CameraError
)
from src.utils.async_processor import AsyncProcessor, parallel_map


class TestMemoryCache:
    """内存缓存测试"""
    
    def test_basic_operations(self):
        """测试基本操作"""
        cache = MemoryCache(max_size=10)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", "value2", ttl=1)
        assert cache.get("key2") == "value2"
    
    def test_expiration(self):
        """测试过期"""
        cache = MemoryCache()
        
        cache.set("key", "value", ttl=0.1)
        assert cache.get("key") == "value"
        
        time.sleep(0.15)
        assert cache.get("key") is None
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = MemoryCache(max_size=3)
        
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        # 访问a，使其变为最近使用
        cache.get("a")
        
        # 添加d，应该淘汰b
        cache.set("d", 4)
        
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4
    
    def test_stats(self):
        """测试统计信息"""
        cache = MemoryCache()
        
        cache.set("key", "value")
        cache.get("key")  # hit
        cache.get("missing")  # miss
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5


class TestLRUCache:
    """LRU缓存测试"""
    
    def test_basic_operations(self):
        """测试基本操作"""
        cache = LRUCache(capacity=3)
        
        cache.put("a", 1)
        cache.put("b", 2)
        
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") is None
    
    def test_capacity_limit(self):
        """测试容量限制"""
        cache = LRUCache(capacity=2)
        
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # 应该淘汰a
        
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3


class TestFunctionCache:
    """函数缓存测试"""
    
    def test_cached_decorator(self):
        """测试缓存装饰器"""
        cache = FunctionCache()
        
        call_count = 0
        
        @cache.cached(ttl=1)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        result1 = expensive_function(1, 2)
        result2 = expensive_function(1, 2)  # 应该从缓存获取
        
        assert result1 == result2 == 3
        assert call_count == 1  # 只调用一次


class TestErrorHandler:
    """错误处理测试"""
    
    def test_handle_errors_decorator(self):
        """测试错误处理装饰器"""
        
        @handle_errors(default_return="fallback")
        def risky_function(should_fail):
            if should_fail:
                raise ValueError("测试错误")
            return "success"
        
        assert risky_function(False) == "success"
        assert risky_function(True) == "fallback"
    
    def test_retry_decorator(self):
        """测试重试装饰器"""
        
        attempt_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def unstable_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("连接失败")
            return "成功"
        
        result = unstable_function()
        assert result == "成功"
        assert attempt_count == 3
    
    def test_safe_execute(self):
        """测试安全执行"""
        
        def risky_func():
            raise ValueError("错误")
        
        result = safe_execute(risky_func, default_return="default")
        assert result == "default"
    
    def test_custom_exceptions(self):
        """测试自定义异常"""
        
        with pytest.raises(CameraError) as exc_info:
            raise CameraError("相机错误", {"device_id": 0})
        
        assert "相机错误" in str(exc_info.value)
        assert exc_info.value.error_code == "CAMERA_ERROR"


class TestAsyncProcessor:
    """异步处理器测试"""
    
    def test_submit(self):
        """测试任务提交"""
        
        with AsyncProcessor(max_workers=2) as processor:
            future = processor.submit(lambda: 42)
            assert future.result() == 42
    
    def test_map(self):
        """测试并行映射"""
        
        with AsyncProcessor(max_workers=2) as processor:
            results = processor.map(lambda x: x * 2, [1, 2, 3, 4])
            assert list(results) == [2, 4, 6, 8]
    
    def test_parallel_map_function(self):
        """测试parallel_map函数"""
        
        results = parallel_map(lambda x: x ** 2, [1, 2, 3, 4], max_workers=2)
        assert results == [1, 4, 9, 16]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
