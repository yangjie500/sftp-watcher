import logging
from typing import Any

logger = logging.getLogger(__name__)


class FromConfigCredentialProvider:
    def __init__(
        self,
        *,
        config: Any,
        password_key: str,
    ) -> None:
        self._config = config
        self._password_key = password_key

    def get_credentials(self) -> str:
        value = getattr(self._config, self._password_key, None)

        if not isinstance(value, str) or not value:
            logger.error(
                "Credential value is missing from config: key=%s",
                self._password_key,
            )
            raise ValueError(
                f"Credential value is required from config key: {self._password_key}"
            )

        return value
