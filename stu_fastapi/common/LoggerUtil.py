#AI生成
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
#定义一个日志类
class Logger:
    _logger = None  # 单例，防止重复初始化
    @classmethod
    def get_logger(cls, name=__name__):
        """
        获取全局 Logger
        """
        if cls._logger:
            return cls._logger

        # 项目根目录（比 os.getcwd() 稳定）
        BASE_DIR = Path(__file__).resolve().parent.parent

        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / "app.log"

        logger = logging.getLogger(name)
        #设置级别
        logger.setLevel(logging.INFO)

        # 防止重复添加 handler
        if not logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
            )

            # 控制台
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            #  日志轮转（10MB 一个，保留5个）
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,# 保留5个
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

        cls._logger = logger
        return logger
if __name__ == '__main__':
    logger = Logger.get_logger()
    logger.info("hello")