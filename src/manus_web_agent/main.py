import logging

from manus_web_agent.core import TOML_CONFIG, get_config

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info(f"Hello from manus-web-agent!: {get_config()}")
    logger.info(f"logger")


if __name__ == "__main__":
    main()
