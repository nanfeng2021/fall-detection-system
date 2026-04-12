#!/usr/bin/env python3
"""
缓存模块
提供内存缓存、LRU缓存、TTL缓存等功能
"""

import time
import hashlib
import pickle
from typing import Any, Optional, Dict, Callable, Tuple
from functools import wraps
from collections import OrderedDict
from threading import Lock
from dataclasses import dataclass
from loguru import logger

from .config import get_performance_config


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    ttl: Optional[int] = None  # 过期时间（秒）
    access_count: int = 0
    last_accessed: float = 0.0
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.access_count += 1
        self.last_accessed = time.time()


class MemoryCache:
    """内存缓存"""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        
        logger.info(f"MemoryCache 初始化: max_size={max_size}, ttl={default_ttl}")
    
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = pickle.dumps((args, sorted(kwargs.items())))
        return hashlib.md5(key_data).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            entry.touch()
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期
        """
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # 如果缓存已满，移除最久未使用的
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                last_accessed=time.time()
            )
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def _evict_lru(self):
        """移除最久未使用的条目"""
        if not self._cache:
            return
        
        # 找到最久未访问的
        lru_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
    
    def cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"清理 {len(expired_keys)} 个过期缓存条目")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'expired_count': sum(1 for e in self._cache.values() if e.is_expired),
        }
    
    def keys(self) -> list:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())
    
    def values(self) -> list:
        """获取所有值"""
        with self._lock:
            return [e.value for e in self._cache.values()]
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get(key) is not None
    
    def __len__(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class LRUCache(OrderedDict):
    """LRU缓存（基于OrderedDict）"""
    
    def __init__(self, capacity: int = 100):
        """
        初始化LRU缓存
        
        Args:
            capacity: 缓存容量
        """
        super().__init__()
        self.capacity = capacity
        self._lock = Lock()
    
    def get(self, key: Any) -> Any:
        """获取值并移到末尾（最近使用）"""
        with self._lock:
            if key not in self:
                return None
            self.move_to_end(key)
            return self[key]
    
    def put(self, key: Any, value: Any):
        """设置值"""
        with self._lock:
            if key in self:
                self.move_to_end(key)
            self[key] = value
            
            if len(self) > self.capacity:
                self.popitem(last=False)


class FunctionCache:
    """函数结果缓存"""
    
    def __init__(self, cache: Optional[MemoryCache] = None):
        """
        初始化函数缓存
        
        Args:
            cache: 缓存实例，None则创建新实例
        """
        self.cache = cache or MemoryCache()
    
    def cached(self, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
        """
        装饰器：缓存函数结果
        
        Args:
            ttl: 过期时间（秒）
            key_func: 自定义键生成函数
            
        使用示例:
            @cache.cached(ttl=60)
            def expensive_function(x, y):
                # 耗时计算
                return result
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._make_key(func.__name__, *args, **kwargs)
                
                # 尝试从缓存获取
                result = self.cache.get(cache_key)
                if result is not None:
                    return result
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 存入缓存
                self.cache.set(cache_key, result, ttl)
                
                return result
            
            # 附加缓存控制方法
            wrapper.cache_clear = lambda: self.cache.clear()
            wrapper.cache_info = self.cache.get_stats
            
            return wrapper
        return decorator
    
    def _make_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = pickle.dumps((func_name, args, sorted(kwargs.items())))
        return hashlib.md5(key_data).hexdigest()


class PointCloudCache:
    """点云专用缓存"""
    
    def __init__(self, max_size: int = 50):
        """
        初始化点云缓存
        
        Args:
            max_size: 最大缓存帧数
        """
        self.cache = MemoryCache(max_size=max_size, default_ttl=30)
        self._frame_index = 0
    
    def cache_frame(self, frame_id: int, point_cloud: Any, 
                    processing_result: Optional[Any] = None):
        """
        缓存帧数据
        
        Args:
            frame_id: 帧ID
            point_cloud: 点云数据
            processing_result: 处理结果（可选）
        """
        self.cache.set(
            f"frame_{frame_id}",
            {
                'frame_id': frame_id,
                'point_cloud': point_cloud,
                'result': processing_result,
                'timestamp': time.time(),
            },
            ttl=30
        )
    
    def get_frame(self, frame_id: int) -> Optional[Dict]:
        """获取缓存的帧"""
        return self.cache.get(f"frame_{frame_id}")
    
    def get_latest_frames(self, count: int = 10) -> list:
        """获取最近的几帧"""
        frames = []
        for i in range(max(0, self._frame_index - count), self._frame_index):
            frame = self.get_frame(i)
            if frame:
                frames.append(frame)
        return frames
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.cache.get_stats()


# 全局缓存实例
_global_cache: Optional[MemoryCache] = None
_global_lock = Lock()


def get_cache() -> MemoryCache:
    """获取全局缓存实例"""
    global _global_cache
    
    with _global_lock:
        if _global_cache is None:
            config = get_performance_config()
            _global_cache = MemoryCache(
                max_size=config.cache_max_size or 1000,
                default_ttl=config.cache_ttl or 60
            )
        return _global_cache


def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    装饰器：缓存函数结果（使用全局缓存）
    
    使用示例:
        @cached(ttl=60)
        def expensive_function(x, y):
            return result
    """
    cache = get_cache()
    func_cache = FunctionCache(cache)
    return func_cache.cached(ttl=ttl, key_func=key_func)


def clear_cache():
    """清空全局缓存"""
    cache = get_cache()
    cache.clear()
    logger.info("全局缓存已清空")


def get_cache_stats() -> Dict:
    """获取全局缓存统计"""
    return get_cache().get_stats()


# 测试代码
if __name__ == "__main__":
    print("🧪 测试缓存模块...")
    
    # 测试1: 基本缓存操作
    print("\n1️⃣ 测试基本缓存操作...")
    
    cache = MemoryCache(max_size=5, default_ttl=2)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2", ttl=1)
    
    print(f"  key1: {cache.get('key1')}")
    print(f"  key2: {cache.get('key2')}")
    
    # 测试过期
    print("  等待1秒...")
    time.sleep(1.1)
    print(f"  key1 (未过期): {cache.get('key1')}")
    print(f"  key2 (已过期): {cache.get('key2')}")
    
    # 测试2: LRU淘汰
    print("\n2️⃣ 测试LRU淘汰...")
    
    cache2 = MemoryCache(max_size=3)
    cache2.set("a", 1)
    cache2.set("b", 2)
    cache2.set("c", 3)
    
    print(f"  初始: {list(cache2.keys())}")
    
    # 访问a，使其变为最近使用
    cache2.get("a")
    
    # 添加d，应该淘汰b
    cache2.set("d", 4)
    print(f"  添加d后: {list(cache2.keys())}")
    
    # 测试3: 函数缓存装饰器
    print("\n3️⃣ 测试函数缓存装饰器...")
    
    class Counter:
        def __init__(self):
            self.count = 0
    
    counter = Counter()
    
    @cached(ttl=2)
    def expensive_computation(x, y):
        counter.count += 1
        time.sleep(0.1)
        return x + y
    
    result1 = expensive_computation(1, 2)
    result2 = expensive_computation(1, 2)  # 应该从缓存获取
    result3 = expensive_computation(2, 3)  # 新参数
    
    print(f"  结果1: {result1}")
    print(f"  结果2: {result2}")
    print(f"  结果3: {result3}")
    print(f"  实际调用次数: {counter.count} (期望: 2)")
    
    # 测试4: 点云缓存
    print("\n4️⃣ 测试点云缓存...")
    
    pc_cache = PointCloudCache(max_size=10)
    
    for i in range(5):
        pc_cache.cache_frame(i, f"point_cloud_{i}", f"result_{i}")
    
    frame = pc_cache.get_frame(2)
    print(f"  帧2: {frame}")
    
    latest = pc_cache.get_latest_frames(3)
    print(f"  最近3帧: {[f['frame_id'] for f in latest]}")
    
    print(f"  统计: {pc_cache.get_stats()}")
    
    # 测试5: 缓存统计
    print("\n5️⃣ 测试缓存统计...")
    
    stats = cache.get_stats()
    print(f"  统计信息: {stats}")
    
    print("\n✅ 测试完成!")
