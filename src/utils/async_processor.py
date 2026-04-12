#!/usr/bin/env python3
"""
异步处理模块
提供并发处理、线程池、异步任务管理等功能
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, Any, List, Optional, Dict
from functools import wraps
import time
from queue import Queue
from dataclasses import dataclass
from loguru import logger

from .config import get_performance_config


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False):
        """
        初始化异步处理器
        
        Args:
            max_workers: 最大工作线程/进程数
            use_processes: 是否使用进程池（CPU密集型任务）
        """
        config = get_performance_config()
        self.max_workers = max_workers or config.max_workers
        self.use_processes = use_processes or config.use_process_pool
        
        self._executor: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        
        self._init_executor()
        
        logger.info(f"AsyncProcessor 初始化: workers={self.max_workers}, "
                   f"use_processes={self.use_processes}")
    
    def _init_executor(self):
        """初始化执行器"""
        if self.use_processes:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 获取或创建事件循环
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            Future对象
        """
        if self._executor is None:
            raise RuntimeError("执行器未初始化")
        
        return self._executor.submit(func, *args, **kwargs)
    
    def map(self, func: Callable, iterable: List[Any]) -> List[Any]:
        """
        并行映射处理
        
        Args:
            func: 处理函数
            iterable: 输入列表
            
        Returns:
            结果列表
        """
        if self._executor is None:
            raise RuntimeError("执行器未初始化")
        
        return list(self._executor.map(func, iterable))
    
    async def async_submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步提交任务
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            执行结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class FrameBuffer:
    """帧缓冲区 - 用于异步帧处理"""
    
    def __init__(self, maxsize: int = 10):
        """
        初始化帧缓冲区
        
        Args:
            maxsize: 缓冲区最大容量
        """
        self._queue: Queue = Queue(maxsize=maxsize)
        self._drop_count = 0
        self._processed_count = 0
        
    def put(self, frame: Any, block: bool = False) -> bool:
        """
        放入帧
        
        Args:
            frame: 帧数据
            block: 是否阻塞等待
            
        Returns:
            是否成功放入
        """
        try:
            self._queue.put(frame, block=block)
            return True
        except:
            self._drop_count += 1
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """
        取出帧
        
        Args:
            block: 是否阻塞等待
            timeout: 超时时间
            
        Returns:
            帧数据或None
        """
        try:
            frame = self._queue.get(block=block, timeout=timeout)
            self._processed_count += 1
            return frame
        except:
            return None
    
    def clear(self):
        """清空缓冲区"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except:
                break
    
    @property
    def size(self) -> int:
        """当前缓冲区大小"""
        return self._queue.qsize()
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return self._queue.empty()
    
    @property
    def is_full(self) -> bool:
        """是否已满"""
        return self._queue.full()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'size': self.size,
            'maxsize': self._queue.maxsize,
            'dropped': self._drop_count,
            'processed': self._processed_count,
        }


class PipelineStage:
    """流水线处理阶段"""
    
    def __init__(self, name: str, processor: Callable, 
                 async_mode: bool = False, max_workers: int = 1):
        """
        初始化处理阶段
        
        Args:
            name: 阶段名称
            processor: 处理函数
            async_mode: 是否异步处理
            max_workers: 最大工作线程数
        """
        self.name = name
        self.processor = processor
        self.async_mode = async_mode
        self.max_workers = max_workers
        
        self._executor: Optional[ThreadPoolExecutor] = None
        if async_mode:
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        self._stats = {
            'processed': 0,
            'errors': 0,
            'total_time_ms': 0.0,
        }
    
    def process(self, data: Any) -> Any:
        """处理数据"""
        start_time = time.time()
        
        try:
            if self.async_mode and self._executor:
                future = self._executor.submit(self.processor, data)
                result = future.result()
            else:
                result = self.processor(data)
            
            self._stats['processed'] += 1
            return result
            
        except Exception as e:
            logger.error(f"阶段 {self.name} 处理失败: {e}")
            self._stats['errors'] += 1
            raise
        finally:
            self._stats['total_time_ms'] += (time.time() - start_time) * 1000
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        avg_time = (self._stats['total_time_ms'] / max(self._stats['processed'], 1))
        return {
            **self._stats,
            'average_time_ms': avg_time,
        }
    
    def shutdown(self):
        """关闭执行器"""
        if self._executor:
            self._executor.shutdown(wait=True)


class AsyncPipeline:
    """异步处理流水线"""
    
    def __init__(self, name: str = "pipeline"):
        """
        初始化流水线
        
        Args:
            name: 流水线名称
        """
        self.name = name
        self._stages: List[PipelineStage] = []
        self._buffer = FrameBuffer(maxsize=5)
        
    def add_stage(self, name: str, processor: Callable, 
                  async_mode: bool = False, max_workers: int = 1):
        """
        添加处理阶段
        
        Args:
            name: 阶段名称
            processor: 处理函数
            async_mode: 是否异步处理
            max_workers: 最大工作线程数
        """
        stage = PipelineStage(name, processor, async_mode, max_workers)
        self._stages.append(stage)
        logger.info(f"流水线 {self.name}: 添加阶段 {name} (async={async_mode})")
        return self
    
    def process(self, data: Any) -> Any:
        """
        处理数据
        
        Args:
            data: 输入数据
            
        Returns:
            处理结果
        """
        result = data
        for stage in self._stages:
            result = stage.process(result)
        return result
    
    def process_batch(self, data_list: List[Any]) -> List[Any]:
        """
        批量处理
        
        Args:
            data_list: 数据列表
            
        Returns:
            结果列表
        """
        return [self.process(d) for d in data_list]
    
    def get_stats(self) -> Dict:
        """获取流水线统计信息"""
        return {
            'name': self.name,
            'stages': len(self._stages),
            'stage_stats': {s.name: s.get_stats() for s in self._stages},
            'buffer_stats': self._buffer.get_stats(),
        }
    
    def shutdown(self):
        """关闭流水线"""
        for stage in self._stages:
            stage.shutdown()


def async_task(func: Callable) -> Callable:
    """
    装饰器：将函数转换为异步任务
    
    使用示例:
        @async_task
        def my_heavy_function(data):
            # 耗时操作
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        processor = AsyncProcessor()
        try:
            future = processor.submit(func, *args, **kwargs)
            return future.result()
        finally:
            processor.shutdown()
    
    return wrapper


def parallel_map(func: Callable, items: List[Any], max_workers: Optional[int] = None) -> List[Any]:
    """
    并行映射处理
    
    Args:
        func: 处理函数
        items: 输入列表
        max_workers: 最大工作线程数
        
    Returns:
        结果列表
    """
    with AsyncProcessor(max_workers=max_workers) as processor:
        return processor.map(func, items)


# 全局异步处理器实例
_global_processor: Optional[AsyncProcessor] = None
_global_lock = threading.Lock()


def get_async_processor() -> AsyncProcessor:
    """获取全局异步处理器"""
    global _global_processor
    
    with _global_lock:
        if _global_processor is None:
            _global_processor = AsyncProcessor()
        return _global_processor


def shutdown_async_processor():
    """关闭全局异步处理器"""
    global _global_processor
    
    with _global_lock:
        if _global_processor:
            _global_processor.shutdown()
            _global_processor = None


# 测试代码
if __name__ == "__main__":
    print("🧪 测试异步处理模块...")
    
    # 测试1: 基本异步提交
    print("\n1️⃣ 测试异步提交...")
    
    def heavy_computation(n):
        time.sleep(0.1)
        return n * n
    
    with AsyncProcessor(max_workers=4) as processor:
        futures = [processor.submit(heavy_computation, i) for i in range(5)]
        results = [f.result() for f in futures]
        print(f"  结果: {results}")
    
    # 测试2: 并行映射
    print("\n2️⃣ 测试并行映射...")
    
    def process_item(x):
        time.sleep(0.05)
        return x * 2
    
    items = list(range(10))
    results = parallel_map(process_item, items, max_workers=4)
    print(f"  输入: {items}")
    print(f"  输出: {results}")
    
    # 测试3: 流水线
    print("\n3️⃣ 测试流水线...")
    
    pipeline = AsyncPipeline("test_pipeline")
    pipeline.add_stage("stage1", lambda x: x + 1)
    pipeline.add_stage("stage2", lambda x: x * 2)
    pipeline.add_stage("stage3", lambda x: x - 3)
    
    result = pipeline.process(5)
    print(f"  输入: 5")
    print(f"  输出: {result}")  # (5+1)*2-3 = 9
    
    stats = pipeline.get_stats()
    print(f"  统计: {stats}")
    
    pipeline.shutdown()
    
    # 测试4: 帧缓冲区
    print("\n4️⃣ 测试帧缓冲区...")
    
    buffer = FrameBuffer(maxsize=3)
    for i in range(5):
        success = buffer.put(i, block=False)
        print(f"  放入 {i}: {'成功' if success else '失败'}")
    
    print(f"  缓冲区统计: {buffer.get_stats()}")
    
    print("\n✅ 测试完成!")
