#!/usr/bin/env python3
"""
错误处理模块
提供统一的异常处理、错误日志、重试机制等功能
"""

import sys
import traceback
import functools
import time
from typing import Callable, Any, Optional, Type, Tuple, List
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: str
    message: str
    severity: ErrorSeverity
    traceback_str: str
    timestamp: float
    function_name: Optional[str] = None
    args: Optional[tuple] = None
    kwargs: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'severity': self.severity.value,
            'traceback': self.traceback_str,
            'timestamp': self.timestamp,
            'function': self.function_name,
        }


class FallDetectionError(Exception):
    """摔倒检测系统基础异常"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"[{self.error_code}] {self.message} - Details: {self.details}"
        return f"[{self.error_code}] {self.message}"


class CameraError(FallDetectionError):
    """相机相关错误"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "CAMERA_ERROR", details)


class PreprocessingError(FallDetectionError):
    """预处理错误"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "PREPROCESSING_ERROR", details)


class DetectionError(FallDetectionError):
    """检测错误"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "DETECTION_ERROR", details)


class ConfigurationError(FallDetectionError):
    """配置错误"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self._error_callbacks: List[Callable] = []
        self._error_history: List[ErrorContext] = []
        self._max_history = 100
    
    def handle_error(self, error: Exception, severity: ErrorSeverity = ErrorSeverity.ERROR,
                     function_name: Optional[str] = None, 
                     args: Optional[tuple] = None,
                     kwargs: Optional[dict] = None) -> ErrorContext:
        """
        处理错误
        
        Args:
            error: 异常对象
            severity: 严重程度
            function_name: 函数名
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            错误上下文
        """
        # 获取堆栈信息
        tb_str = traceback.format_exc()
        
        # 创建错误上下文
        context = ErrorContext(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            traceback_str=tb_str,
            timestamp=time.time(),
            function_name=function_name,
            args=args,
            kwargs=kwargs
        )
        
        # 记录到历史
        self._error_history.append(context)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
        
        # 根据严重程度记录日志
        log_message = f"[{context.error_type}] {context.message}"
        if function_name:
            log_message = f"[{function_name}] {log_message}"
        
        if severity == ErrorSeverity.DEBUG:
            logger.debug(log_message)
        elif severity == ErrorSeverity.INFO:
            logger.info(log_message)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_message)
            logger.debug(f"Traceback:\n{tb_str}")
        elif severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
            logger.critical(f"Traceback:\n{tb_str}")
        
        # 调用回调
        for callback in self._error_callbacks:
            try:
                callback(context)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")
        
        return context
    
    def register_callback(self, callback: Callable):
        """注册错误回调"""
        self._error_callbacks.append(callback)
    
    def get_error_history(self, severity: Optional[ErrorSeverity] = None) -> List[ErrorContext]:
        """获取错误历史"""
        if severity:
            return [e for e in self._error_history if e.severity == severity]
        return self._error_history.copy()
    
    def clear_history(self):
        """清空错误历史"""
        self._error_history.clear()


# 全局错误处理器
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler


def safe_execute(func: Callable, *args, default_return: Any = None,
                 severity: ErrorSeverity = ErrorSeverity.ERROR, **kwargs) -> Any:
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        *args, **kwargs: 函数参数
        default_return: 出错时的默认返回值
        severity: 错误严重程度
        
    Returns:
        函数结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        get_error_handler().handle_error(
            e, severity=severity, function_name=func.__name__, args=args, kwargs=kwargs
        )
        return default_return


def retry(max_attempts: int = 3, delay: float = 1.0, 
          exceptions: Tuple[Type[Exception], ...] = (Exception,),
          on_retry: Optional[Callable] = None):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 要捕获的异常类型
        on_retry: 重试时的回调函数
        
    使用示例:
        @retry(max_attempts=3, delay=1.0)
        def unstable_function():
            # 可能失败的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt} 次尝试失败: {e}，"
                            f"{delay}秒后重试..."
                        )
                        
                        if on_retry:
                            try:
                                on_retry(attempt, e)
                            except Exception as callback_error:
                                logger.error(f"重试回调失败: {callback_error}")
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败"
                        )
            
            # 所有重试都失败
            raise last_exception
        
        return wrapper
    return decorator


def handle_errors(default_return: Any = None, 
                  severity: ErrorSeverity = ErrorSeverity.ERROR,
                  reraise: bool = False):
    """
    错误处理装饰器
    
    Args:
        default_return: 出错时的默认返回值
        severity: 错误严重程度
        reraise: 是否重新抛出异常
        
    使用示例:
        @handle_errors(default_return=None)
        def risky_function():
            # 可能抛出异常的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                get_error_handler().handle_error(
                    e, severity=severity, function_name=func.__name__,
                    args=args, kwargs=kwargs
                )
                
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    return decorator


def validate_input(validator: Callable, error_message: str = "输入验证失败"):
    """
    输入验证装饰器
    
    Args:
        validator: 验证函数，返回bool
        error_message: 验证失败时的错误信息
        
    使用示例:
        @validate_input(lambda x: x > 0, "x必须大于0")
        def process_positive(x):
            return x * 2
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not validator(*args, **kwargs):
                raise ValueError(error_message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class ContextManager:
    """上下文管理器 - 确保资源正确释放"""
    
    def __init__(self, enter_func: Optional[Callable] = None,
                 exit_func: Optional[Callable] = None):
        self.enter_func = enter_func
        self.exit_func = exit_func
    
    def __enter__(self):
        if self.enter_func:
            self.enter_func()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.exit_func:
            try:
                self.exit_func()
            except Exception as e:
                logger.error(f"退出函数执行失败: {e}")
        
        # 不抑制异常
        return False


def setup_global_exception_handler():
    """设置全局异常处理器"""
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """全局异常处理"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 保留键盘中断的默认行为
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("未捕获的异常:")
        logger.critical("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    
    sys.excepthook = global_exception_handler


# 测试代码
if __name__ == "__main__":
    print("🧪 测试错误处理模块...")
    
    # 测试1: 基本错误处理
    print("\n1️⃣ 测试基本错误处理...")
    
    @handle_errors(default_return="fallback", severity=ErrorSeverity.WARNING)
    def risky_function(should_fail):
        if should_fail:
            raise ValueError("模拟错误")
        return "success"
    
    result1 = risky_function(False)
    result2 = risky_function(True)
    
    print(f"  正常结果: {result1}")
    print(f"  错误结果: {result2}")
    
    # 测试2: 重试机制
    print("\n2️⃣ 测试重试机制...")
    
    attempt_count = 0
    
    @retry(max_attempts=3, delay=0.1)
    def unstable_function():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("连接失败")
        return "成功"
    
    try:
        result = unstable_function()
        print(f"  结果: {result}")
        print(f"  尝试次数: {attempt_count}")
    except Exception as e:
        print(f"  最终失败: {e}")
    
    # 测试3: 自定义异常
    print("\n3️⃣ 测试自定义异常...")
    
    try:
        raise CameraError("相机连接失败", {"device_id": 0})
    except FallDetectionError as e:
        print(f"  捕获异常: {e}")
        print(f"  错误码: {e.error_code}")
        print(f"  详情: {e.details}")
    
    # 测试4: 错误处理器
    print("\n4️⃣ 测试错误处理器...")
    
    handler = ErrorHandler()
    
    def my_callback(context):
        print(f"  回调收到错误: {context.message}")
    
    handler.register_callback(my_callback)
    
    try:
        raise ValueError("测试错误")
    except Exception as e:
        context = handler.handle_error(e, severity=ErrorSeverity.INFO)
        print(f"  错误上下文: {context.error_type}")
    
    # 测试5: 输入验证
    print("\n5️⃣ 测试输入验证...")
    
    @validate_input(lambda x: x > 0, "x必须大于0")
    def process_positive(x):
        return x * 2
    
    try:
        result = process_positive(5)
        print(f"  process_positive(5) = {result}")
        
        result = process_positive(-1)
    except ValueError as e:
        print(f"  验证失败: {e}")
    
    print("\n✅ 测试完成!")
