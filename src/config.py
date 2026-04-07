"""配置管理模块 - 从 TOML 文件加载配置"""

import sys
from pathlib import Path
from typing import Optional

import tomllib


class Config:
    """AID 配置类"""

    def __init__(self):
        self._config = {}
        self._loaded = False
        self._load()

    def _load(self) -> None:
        """从 TOML 文件加载配置"""
        if self._loaded:
            return

        config_paths = [
            self._get_executable_dir() / "config.toml",
            Path.cwd() / "config.toml",
            Path(__file__).parent.parent / "config.toml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "rb") as f:
                        self._config = tomllib.load(f)
                    self._loaded = True
                    print(f"[成功] 已加载配置文件: {config_path}")
                    return
                except Exception as e:
                    print(f"[警告] 加载配置文件失败: {e}")

        print("[警告] 未找到配置文件，使用默认值")
        self._config = {}
        self._loaded = True

    def _get_executable_dir(self) -> Path:
        """获取可执行文件/脚本所在目录"""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent.parent

    def get(self, *keys: str, default: Optional[str] = None) -> Optional[str]:
        """获取配置值，支持嵌套键"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        if isinstance(value, (int, float, bool)):
            return str(value)
        return value if isinstance(value, str) else default

    def get_int(self, *keys: str, default: int = 0) -> int:
        """获取整数配置值"""
        value = self.get(*keys)
        if value is not None:
            try:
                return int(value)
            except ValueError:
                pass
        return default

    def get_float(self, *keys: str, default: float = 0.0) -> float:
        """获取浮点数配置值"""
        value = self.get(*keys)
        if value is not None:
            try:
                return float(value)
            except ValueError:
                pass
        return default

    def get_bool(self, *keys: str, default: bool = False) -> bool:
        """获取布尔配置值"""
        value = self.get(*keys)
        if value is not None:
            return value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
        return default

    def get_optional(self, *keys: str) -> Optional[str]:
        """获取可选配置值（可能为 None）"""
        return self.get(*keys, default=None)

    @property
    def modelscope_api_key(self) -> Optional[str]:
        return self.get_optional("modelscope", "api_key")

    @property
    def modelscope_base_url(self) -> str:
        return self.get("modelscope", "base_url", default="https://api-inference.modelscope.cn/v1")

    @property
    def modelscope_model(self) -> str:
        return self.get("modelscope", "model", default="Qwen/Qwen3.5-27B")

    @property
    def openrouter_api_key(self) -> Optional[str]:
        return self.get_optional("openrouter", "api_key")

    @property
    def openrouter_base_url(self) -> str:
        return self.get("openrouter", "base_url", default="https://openrouter.ai/api/v1")

    @property
    def openrouter_model(self) -> str:
        return self.get("openrouter", "model", default="qwen/qwen-2.5-72b-instruct")

    @property
    def llm_temperature(self) -> float:
        return self.get_float("llm", "temperature", default=0.7)

    @property
    def server_port(self) -> int:
        return self.get_int("server", "port", default=7860)

    @property
    def tavily_api_key(self) -> Optional[str]:
        return self.get_optional("search", "api_key")

    @property
    def tencent_map_key(self) -> Optional[str]:
        return self.get_optional("location", "tencent_key")

    @property
    def tencent_map_sk(self) -> Optional[str]:
        return self.get_optional("location", "tencent_sk")


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config
