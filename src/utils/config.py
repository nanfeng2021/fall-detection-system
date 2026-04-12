#!/usr/bin/env python3
"""
配置管理模块
统一管理系统配置，支持 YAML 配置文件和环境变量覆盖
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "GuardianFall"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    log_dir: str = "./logs"


@dataclass
class CameraConfig:
    """相机配置"""
    type: str = "azure_kinect"
    device_id: int = 0
    depth_mode: str = "nfov_unbinned"
    color_resolution: str = "off"
    fps: int = 30


@dataclass
class RecordingConfig:
    """录制配置"""
    enabled: bool = False
    output_dir: str = "./datasets/recordings"
    max_duration_seconds: int = 300
    auto_save: bool = True


@dataclass
class DataCaptureConfig:
    """数据采集配置"""
    camera: CameraConfig = field(default_factory=CameraConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)


@dataclass
class VoxelFilterConfig:
    """体素滤波配置"""
    enabled: bool = True
    leaf_size: float = 0.05


@dataclass
class StatisticalFilterConfig:
    """统计滤波配置"""
    enabled: bool = True
    nb_neighbors: int = 20
    std_ratio: float = 2.0


@dataclass
class GroundSegmentationConfig:
    """地面分割配置"""
    enabled: bool = True
    method: str = "plane"
    distance_threshold: float = 0.05
    max_iterations: int = 100


@dataclass
class ClusteringConfig:
    """聚类配置"""
    method: str = "euclidean"
    cluster_tolerance: float = 0.1
    min_cluster_size: int = 50
    max_cluster_size: int = 5000


@dataclass
class HumanFilterConfig:
    """人体筛选配置"""
    min_height: float = 0.5
    max_height: float = 2.5
    min_points: int = 50
    min_aspect_ratio: float = 1.5


@dataclass
class PreprocessingConfig:
    """预处理配置"""
    voxel_filter: VoxelFilterConfig = field(default_factory=VoxelFilterConfig)
    statistical_filter: StatisticalFilterConfig = field(default_factory=StatisticalFilterConfig)
    ground_segmentation: GroundSegmentationConfig = field(default_factory=GroundSegmentationConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    human_filter: HumanFilterConfig = field(default_factory=HumanFilterConfig)


@dataclass
class DetectionRulesConfig:
    """检测规则配置"""
    height_drop_threshold: float = 0.3
    velocity_threshold: float = 0.5
    lying_aspect_ratio: float = 1.5
    confirmation_frames: int = 2


@dataclass
class DetectionConfig:
    """摔倒检测配置"""
    rules: DetectionRulesConfig = field(default_factory=DetectionRulesConfig)


@dataclass
class WebConfig:
    """Web界面配置"""
    server_address: str = "0.0.0.0"
    server_port: int = 8501
    headless: bool = True


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    cache_enabled: bool = True
    cache_ttl: int = 60


@dataclass
class Config:
    """主配置类"""
    system: SystemConfig = field(default_factory=SystemConfig)
    data_capture: DataCaptureConfig = field(default_factory=DataCaptureConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    web: WebConfig = field(default_factory=WebConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> Config:
        """加载配置"""
        # 默认配置
        config = Config()
        
        # 从 YAML 文件加载
        config_file = self._find_config_file()
        if config_file:
            config = self._load_from_yaml(config_file, config)
        
        # 环境变量覆盖
        config = self._apply_env_overrides(config)
        
        return config
    
    def _find_config_file(self) -> Optional[Path]:
        """查找配置文件"""
        possible_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("/app/config.yaml"),
            Path(os.environ.get("CONFIG_PATH", "")),
        ]
        
        for path in possible_paths:
            if path and path.exists():
                return path
        
        return None
    
    def _load_from_yaml(self, config_file: Path, default_config: Config) -> Config:
        """从 YAML 加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return default_config
            
            # 递归更新配置
            return self._update_config_from_dict(default_config, data)
            
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}")
            return default_config
    
    def _update_config_from_dict(self, config: Any, data: Dict) -> Any:
        """从字典更新配置对象"""
        if not isinstance(config, (Config, SystemConfig, DataCaptureConfig, 
                                   PreprocessingConfig, DetectionConfig, WebConfig,
                                   PerformanceConfig, CameraConfig, RecordingConfig,
                                   VoxelFilterConfig, StatisticalFilterConfig,
                                   GroundSegmentationConfig, ClusteringConfig,
                                   HumanFilterConfig, DetectionRulesConfig)):
            return config
        
        for key, value in data.items():
            if hasattr(config, key):
                attr = getattr(config, key)
                if isinstance(value, dict) and hasattr(attr, '__dataclass_fields__'):
                    # 递归更新嵌套配置
                    setattr(config, key, self._update_config_from_dict(attr, value))
                else:
                    setattr(config, key, value)
        
        return config
    
    def _apply_env_overrides(self, config: Config) -> Config:
        """应用环境变量覆盖"""
        # 系统配置
        if os.getenv('LOG_LEVEL'):
            config.system.log_level = os.getenv('LOG_LEVEL')
        if os.getenv('DEBUG'):
            config.system.debug = os.getenv('DEBUG').lower() == 'true'
        
        # Web配置
        if os.getenv('STREAMLIT_SERVER_PORT'):
            config.web.server_port = int(os.getenv('STREAMLIT_SERVER_PORT'))
        if os.getenv('STREAMLIT_SERVER_ADDRESS'):
            config.web.server_address = os.getenv('STREAMLIT_SERVER_ADDRESS')
        if os.getenv('STREAMLIT_SERVER_HEADLESS'):
            config.web.headless = os.getenv('STREAMLIT_SERVER_HEADLESS').lower() == 'true'
        
        # 检测配置
        if os.getenv('DETECTION_HEIGHT_THRESHOLD'):
            config.detection.rules.height_drop_threshold = float(os.getenv('DETECTION_HEIGHT_THRESHOLD'))
        if os.getenv('DETECTION_VELOCITY_THRESHOLD'):
            config.detection.rules.velocity_threshold = float(os.getenv('DETECTION_VELOCITY_THRESHOLD'))
        if os.getenv('DETECTION_CONFIRMATION_FRAMES'):
            config.detection.rules.confirmation_frames = int(os.getenv('DETECTION_CONFIRMATION_FRAMES'))
        
        return config
    
    @property
    def config(self) -> Config:
        """获取配置"""
        return self._config
    
    def reload(self):
        """重新加载配置"""
        self._config = self._load_config()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
            return obj
        
        return dataclass_to_dict(self._config)


# 全局配置实例
@lru_cache()
def get_config() -> Config:
    """获取全局配置实例"""
    return ConfigManager().config


# 便捷访问函数
def get_system_config() -> SystemConfig:
    return get_config().system

def get_data_capture_config() -> DataCaptureConfig:
    return get_config().data_capture

def get_preprocessing_config() -> PreprocessingConfig:
    return get_config().preprocessing

def get_detection_config() -> DetectionConfig:
    return get_config().detection

def get_web_config() -> WebConfig:
    return get_config().web

def get_performance_config() -> PerformanceConfig:
    return get_config().performance


# 测试代码
if __name__ == "__main__":
    print("🧪 测试配置管理模块...")
    
    config = get_config()
    
    print("\n📋 系统配置:")
    print(f"  名称: {config.system.name}")
    print(f"  版本: {config.system.version}")
    print(f"  日志级别: {config.system.log_level}")
    
    print("\n📷 相机配置:")
    print(f"  类型: {config.data_capture.camera.type}")
    print(f"  深度模式: {config.data_capture.camera.depth_mode}")
    print(f"  FPS: {config.data_capture.camera.fps}")
    
    print("\n🔧 预处理配置:")
    print(f"  体素尺寸: {config.preprocessing.voxel_filter.leaf_size}")
    print(f"  聚类方法: {config.preprocessing.clustering.method}")
    
    print("\n🎯 检测配置:")
    print(f"  高度阈值: {config.detection.rules.height_drop_threshold}")
    print(f"  速度阈值: {config.detection.rules.velocity_threshold}")
    
    print("\n🌐 Web配置:")
    print(f"  地址: {config.web.server_address}")
    print(f"  端口: {config.web.server_port}")
    
    print("\n✅ 配置加载成功!")
