"""
配置管理器 - 统一管理模型配置
"""

import os
import yaml
import logging
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置数据类"""
    name: str
    description: str


@dataclass
class ProcessorConfig:
    """处理器配置数据类"""
    type: str
    name: str
    description: str
    enabled: bool
    default_model: str
    env_vars: Dict[str, str]
    models: Dict[str, ModelConfig]


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: Optional[str] = None) -> None:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为同目录下的 models.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "models.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            # 解析配置
            self._config = self._parse_config(raw_config)
            logger.info(f"Configuration loaded successfully from {config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            # 使用默认配置
            self._config = self._get_default_config()
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            self._config = self._get_default_config()
            
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            self._config = self._get_default_config()
    
    def _parse_config(self, raw_config: Dict) -> Dict:
        """解析原始配置为结构化数据"""
        parsed_config = {
            'defaults': raw_config.get('defaults', {}),
            'processors': {}
        }
        
        # 解析处理器配置
        for processor_type, processor_data in raw_config.get('processors', {}).items():
            models = {}
            for model_name, model_data in processor_data.get('models', {}).items():
                models[model_name] = ModelConfig(
                    name=model_data['name'],
                    description=model_data['description']
                )
            
            parsed_config['processors'][processor_type] = ProcessorConfig(
                type=processor_data['type'],
                name=processor_data['name'],
                description=processor_data['description'],
                enabled=processor_data['enabled'],
                default_model=processor_data['default_model'],
                env_vars=processor_data['env_vars'],
                models=models
            )
        
        return parsed_config
    
    def _get_default_config(self) -> Dict:
        """获取默认配置（当配置文件加载失败时使用）"""
        logger.warning("Using default configuration due to config file loading failure")
        return {
            'defaults': {'processor': 'mock'},
            'processors': {
                'mock': ProcessorConfig(
                    type='mock',
                    name='Mock Processor',
                    description='Emergency fallback mock processor',
                    enabled=True,
                    default_model='mock-v1.0',
                    env_vars={},
                    models={
                        'mock-v1.0': ModelConfig(
                            name='mock-v1.0',
                            description='Emergency fallback model'
                        )
                    }
                )
            }
        }
    
    def get_processor_config(self, processor_type: str) -> Optional[ProcessorConfig]:
        """获取指定处理器的配置"""
        return self._config['processors'].get(processor_type)
    
    def get_available_processors(self) -> List[str]:
        """获取所有可用的处理器类型"""
        return [
            proc_type for proc_type, config in self._config['processors'].items()
            if config.enabled
        ]
    
    def get_model_config(self, processor_type: str, model_name: str) -> Optional[ModelConfig]:
        """获取指定模型的配置"""
        processor_config = self.get_processor_config(processor_type)
        if processor_config:
            return processor_config.models.get(model_name)
        return None
    
    def get_default_model(self, processor_type: str) -> Optional[str]:
        """获取处理器的默认模型"""
        processor_config = self.get_processor_config(processor_type)
        if processor_config:
            # 检查环境变量是否有覆盖
            env_var_name = processor_config.env_vars.get('model_override')
            if env_var_name:
                env_model = os.environ.get(env_var_name)
                if env_model and env_model in processor_config.models:
                    return env_model
            
            return processor_config.default_model
        return None
    
    def get_recommended_models(self, processor_type: str) -> List[str]:
        """获取推荐的模型列表 (现在返回默认模型)"""
        default_model = self.get_default_model(processor_type)
        return [default_model] if default_model else []
    

    
    def get_all_versions(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的模型版本信息
        
        Returns:
            List of version dictionaries for API response
        """
        versions = []
        
        for processor_type, processor_config in self._config['processors'].items():
            if not processor_config.enabled:
                continue
                
            for model_name, model_config in processor_config.models.items():
                versions.append({
                    "processor_type": processor_type,
                    "model_name": model_name,
                    "version_string": f"{processor_type}|{model_name}",
                    "description": model_config.description,
                    "is_default": model_name == processor_config.default_model
                })
        
        return versions
    
    def validate_model_version(self, version_string: str) -> Tuple[Optional[str], Optional[str]]:
        """
        验证并解析模型版本字符串
        
        Args:
            version_string: 格式为 "processor_type|model_name" 或 "model_name"
            
        Returns:
            Tuple of (processor_type, model_name) or (None, None) if invalid
        """
        if '|' in version_string:
            processor_type, model_name = version_string.split('|', 1)
        else:
            # 如果没有分隔符，尝试在所有处理器中查找该模型
            model_name = version_string
            processor_type = None
            
            for proc_type, proc_config in self._config['processors'].items():
                if model_name in proc_config.models:
                    processor_type = proc_type
                    break
            
            if processor_type is None:
                return None, None
        
        # 验证处理器和模型是否存在
        processor_config = self.get_processor_config(processor_type)
        if processor_config and model_name in processor_config.models:
            return processor_type, model_name
        
        return None, None
    
    def get_env_vars_for_processor(self, processor_type: str) -> Dict[str, str]:
        """获取处理器所需的环境变量映射"""
        processor_config = self.get_processor_config(processor_type)
        if processor_config:
            return processor_config.env_vars
        return {}
    
    def reload_config(self) -> None:
        """重新加载配置"""
        logger.info("Reloading configuration...")
        self.load_config()
    
    def get_ip_whitelist_config(self) -> Dict[str, Any]:
        """
        获取 IP 白名单配置（纯环境变量方案）
        
        Returns:
            Dict containing IP whitelist configuration
        """
        # 检查是否启用白名单
        enabled = os.environ.get('IP_WHITELIST_ENABLED', 'false').lower() in ('true', '1', 'yes', 'on')
        
        # 获取允许的 IP 列表
        allowed_ips_str = os.environ.get('ALLOWED_IPS', '').strip()
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()] if allowed_ips_str else []
        
        config = {
            'enabled': enabled,
            'allowed_ips': allowed_ips
        }
        
        if enabled and allowed_ips:
            logger.info(f"IP whitelist enabled with IPs: {allowed_ips}")
        elif enabled:
            logger.info("IP whitelist enabled, only local access allowed")
        else:
            logger.debug("IP whitelist disabled")
        
        return config
    
    def is_ip_allowed(self, client_ip: str) -> bool:
        """
        检查 IP 是否在白名单中（简化版本）
        
        Args:
            client_ip: 客户端IP地址
            
        Returns:
            bool: True if IP is allowed, False otherwise
        """
        try:
            # 1. 本地地址始终允许
            if client_ip in ('127.0.0.1', '::1') or client_ip.lower() == 'localhost':
                logger.debug(f"Local IP '{client_ip}' automatically allowed")
                return True
            
            # 2. 检查是否启用白名单
            enabled = os.environ.get('IP_WHITELIST_ENABLED', 'false').lower() in ('true', '1', 'yes', 'on')
            if not enabled:
                logger.debug("IP whitelist disabled, allowing all access")
                return True
            
            # 3. 获取允许的 IP 列表
            allowed_ips_str = os.environ.get('ALLOWED_IPS', '').strip()
            if not allowed_ips_str:
                logger.warning(f"IP whitelist enabled but no IPs configured, denying access for '{client_ip}'")
                return False
            
            allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()]
            
            # 4. 检查 IP 是否在列表中
            try:
                client_ip_obj = ipaddress.ip_address(client_ip)
            except ValueError as e:
                logger.error(f"Invalid client IP format '{client_ip}': {e}")
                return False
            
            for allowed_ip in allowed_ips:
                if self._ip_matches(client_ip_obj, allowed_ip):
                    logger.debug(f"Client IP '{client_ip}' matches allowed pattern '{allowed_ip}'")
                    return True
            
            logger.warning(f"Client IP '{client_ip}' not in whitelist: {allowed_ips}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking IP whitelist for '{client_ip}': {e}")
            # 出错时默认拒绝访问（安全优先）
            return False
    
    def _ip_matches(self, client_ip_obj, allowed_pattern: str) -> bool:
        """
        检查客户端IP是否匹配允许的模式
        
        Args:
            client_ip_obj: ipaddress.IPv4Address 或 ipaddress.IPv6Address 对象
            allowed_pattern: 允许的IP模式（单个IP或CIDR网段）
            
        Returns:
            bool: True if matches, False otherwise
        """
        try:
            allowed_pattern = allowed_pattern.strip()
            
            # 处理特殊值
            if allowed_pattern.lower() in ('localhost', '127.0.0.1', '::1'):
                # 将 localhost 转换为相应的IP地址
                if allowed_pattern.lower() == 'localhost':
                    return str(client_ip_obj) in ('127.0.0.1', '::1')
                else:
                    return str(client_ip_obj) == allowed_pattern
            
            # 检查是否是CIDR网段
            if '/' in allowed_pattern:
                try:
                    allowed_network = ipaddress.ip_network(allowed_pattern, strict=False)
                    return client_ip_obj in allowed_network
                except ValueError as e:
                    logger.error(f"Invalid CIDR pattern '{allowed_pattern}': {e}")
                    return False
            else:
                # 单个IP地址
                try:
                    allowed_ip_obj = ipaddress.ip_address(allowed_pattern)
                    return client_ip_obj == allowed_ip_obj
                except ValueError as e:
                    logger.error(f"Invalid IP pattern '{allowed_pattern}': {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error matching IP '{client_ip_obj}' against pattern '{allowed_pattern}': {e}")
            return False
    
    def validate_ip_format(self, ip_str: str) -> bool:
        """
        验证 IP 地址格式（支持 CIDR 和特殊值）
        
        Args:
            ip_str: IP地址字符串
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            ip_str = ip_str.strip()
            
            # 检查特殊值
            if ip_str.lower() in ('localhost', '127.0.0.1', '::1'):
                return True
            
            # 检查CIDR网段
            if '/' in ip_str:
                ipaddress.ip_network(ip_str, strict=False)
                return True
            else:
                # 单个IP地址
                ipaddress.ip_address(ip_str)
                return True
                
        except ValueError:
            return False


# 全局配置管理器实例
config_manager = ConfigManager() 