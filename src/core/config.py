import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    _instance = None
    _config_data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """加载 settings.yaml 并覆盖环境变量"""
        config_path = Path("config/settings.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config_data = yaml.safe_load(f)

        # --- 1. LLM 配置 ---
        if 'llm' not in self._config_data:
            self._config_data['llm'] = {}
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("⚠️ Warning: DEEPSEEK_API_KEY not set in .env")
        
        self._config_data['llm']['api_key'] = api_key
        
        # --- 2. 邮箱配置 ---
        if 'email' not in self._config_data:
            self._config_data['email'] = {}
        
        self._config_data['email'].update({
            'host': os.getenv("EMAIL_SMTP_HOST", "smtp.163.com"),
            'port': int(os.getenv("EMAIL_SMTP_PORT", 465)),
            'use_ssl': str(os.getenv("EMAIL_USE_SSL", "true")).lower() == 'true',
            'password': os.getenv("EMAIL_PASSWORD"),
            'sender': os.getenv("EMAIL_SENDER"),
            'receivers': [
                r.strip() 
                for r in (os.getenv("EMAIL_RECEIVERS") or "").split(',') 
                if r.strip()
            ]
        })

    def get(self, key, default=None):
        """安全的获取配置，支持 nested key，例如 'llm.model'"""
        keys = key.split('.')
        value = self._config_data
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    @property
    def root_path(self):
        """
        获取项目的绝对根目录。
        main.py在根目录，且我们从根目录运行。
        config.py 在 src/core/config.py
        所以根目录是 parent.parent.parent
        """

        return Path(__file__).resolve().parent.parent.parent

    @property
    def assets_path(self):
        return self.root_path / "assets"
    
    @property
    def data_path(self):
        return self.root_path / "data"

GlobalConfig = Config()