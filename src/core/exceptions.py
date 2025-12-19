class ScholarCoreError(Exception):
    """ScholarCore 的基类异常"""
    def __init__(self, message: str, code: str = "SCHOLARCORE_ERROR", details: dict = None):
        """
        初始化 ScholarCore 异常
        
        Args:
            message: 错误信息
            code: 错误代码
            details: 详细信息（可选）
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class ConfigurationError(ScholarCoreError):
    """配置缺失或错误"""
    def __init__(self, message: str, config_key: str = None, details: dict = None):
        """
        初始化配置错误
        
        Args:
            message: 错误信息
            config_key: 错误的配置键（可选）
            details: 详细信息（可选）
        """
        code = "CONFIGURATION_ERROR"
        if config_key:
            message = f"{message} (配置项: {config_key})"
        super().__init__(message, code, details)
        self.config_key = config_key


class DriverError(ScholarCoreError):
    """驱动层通用错误"""
    def __init__(self, message: str, driver_name: str = None, details: dict = None):
        """
        初始化驱动错误
        
        Args:
            message: 错误信息
            driver_name: 驱动名称（可选）
            details: 详细信息（可选）
        """
        code = "DRIVER_ERROR"
        if driver_name:
            message = f"{message} (驱动: {driver_name})"
        super().__init__(message, code, details)
        self.driver_name = driver_name


class LLMError(DriverError):
    """LLM API 调用失败 (网络、401、500等)"""
    def __init__(self, message: str, api_provider: str = None, status_code: int = None, details: dict = None):
        """
        初始化 LLM 错误
        
        Args:
            message: 错误信息
            api_provider: API 提供商（可选）
            status_code: HTTP 状态码（可选）
            details: 详细信息（可选）
        """
        code = "LLM_ERROR"
        if api_provider:
            message = f"{message} (提供商: {api_provider})"
        if status_code:
            message = f"{message} (状态码: {status_code})"
        super().__init__(message, "llm", details)
        self.api_provider = api_provider
        self.status_code = status_code


class LLMParseError(LLMError):
    """LLM 返回了内容，但无法解析为 JSON"""
    def __init__(self, message: str, raw_response: str = None, details: dict = None):
        """
        初始化 LLM 解析错误
        
        Args:
            message: 错误信息
            raw_response: LLM 原始响应（可选）
            details: 详细信息（可选）
        """
        code = "LLM_PARSE_ERROR"
        super().__init__(message, None, None, details)
        self.raw_response = raw_response


class FetchError(DriverError):
    """抓取失败 (Arxiv/PDF 下载失败)"""
    def __init__(self, message: str, resource_url: str = None, status_code: int = None, details: dict = None):
        """
        初始化抓取错误
        
        Args:
            message: 错误信息
            resource_url: 资源 URL（可选）
            status_code: HTTP 状态码（可选）
            details: 详细信息（可选）
        """
        code = "FETCH_ERROR"
        if resource_url:
            message = f"{message} (URL: {resource_url})"
        if status_code:
            message = f"{message} (状态码: {status_code})"
        super().__init__(message, "fetch", details)
        self.resource_url = resource_url
        self.status_code = status_code


class ProcessingError(ScholarCoreError):
    """处理层通用错误"""
    def __init__(self, message: str, processor_name: str = None, details: dict = None):
        """
        初始化处理错误
        
        Args:
            message: 错误信息
            processor_name: 处理器名称（可选）
            details: 详细信息（可选）
        """
        code = "PROCESSING_ERROR"
        if processor_name:
            message = f"{message} (处理器: {processor_name})"
        super().__init__(message, code, details)
        self.processor_name = processor_name


class ValidationError(ProcessingError):
    """数据验证失败"""
    def __init__(self, message: str, field_name: str = None, invalid_value: any = None, details: dict = None):
        """
        初始化验证错误
        
        Args:
            message: 错误信息
            field_name: 验证失败的字段名（可选）
            invalid_value: 无效的值（可选）
            details: 详细信息（可选）
        """
        code = "VALIDATION_ERROR"
        if field_name:
            message = f"{message} (字段: {field_name})"
        super().__init__(message, "validator", details)
        self.field_name = field_name
        self.invalid_value = invalid_value


class StorageError(ScholarCoreError):
    """存储层通用错误"""
    def __init__(self, message: str, storage_type: str = None, resource_path: str = None, details: dict = None):
        """
        初始化存储错误
        
        Args:
            message: 错误信息
            storage_type: 存储类型（可选）
            resource_path: 资源路径（可选）
            details: 详细信息（可选）
        """
        code = "STORAGE_ERROR"
        if storage_type:
            message = f"{message} (存储类型: {storage_type})"
        if resource_path:
            message = f"{message} (路径: {resource_path})"
        super().__init__(message, code, details)
        self.storage_type = storage_type
        self.resource_path = resource_path


class ResourceNotFoundError(StorageError):
    """文件不存在"""
    def __init__(self, message: str, file_path: str, details: dict = None):
        """
        初始化文件不存在错误
        
        Args:
            message: 错误信息
            file_path: 文件路径
            details: 详细信息（可选）
        """
        code = "FILE_NOT_FOUND_ERROR"
        super().__init__(message, "file", file_path, details)
        self.file_path = file_path


class FileReadError(StorageError):
    """文件读取失败"""
    def __init__(self, message: str, file_path: str, error: Exception = None, details: dict = None):
        """
        初始化文件读取错误
        
        Args:
            message: 错误信息
            file_path: 文件路径
            error: 原始错误（可选）
            details: 详细信息（可选）
        """
        code = "FILE_READ_ERROR"
        super().__init__(message, "file", file_path, details)
        self.file_path = file_path
        self.original_error = error


class FileWriteError(StorageError):
    """文件写入失败"""
    def __init__(self, message: str, file_path: str, error: Exception = None, details: dict = None):
        """
        初始化文件写入错误
        
        Args:
            message: 错误信息
            file_path: 文件路径
            error: 原始错误（可选）
            details: 详细信息（可选）
        """
        code = "FILE_WRITE_ERROR"
        super().__init__(message, "file", file_path, details)
        self.file_path = file_path
        self.original_error = error