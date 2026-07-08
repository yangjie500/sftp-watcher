from typing import Protocol


class CredentialProvider(Protocol):
    def get_credentials(self) -> str: ...
