import logging.config
import os

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': '/app/logs/bot.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 3,
        }
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
