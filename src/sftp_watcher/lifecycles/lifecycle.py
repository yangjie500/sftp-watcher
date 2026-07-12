from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sftp_watcher.credentials.provider import CredentialProvider
from sftp_watcher.processor.action.aap_client import AAPClient
from sftp_watcher.sftp_client import SFTPClient


@dataclass
class PollLifecycleContext:
    remote_dir: str
    local_dir: Path


class PollLifecycle(Protocol):
    def before_poll(self, context: PollLifecycleContext) -> None: ...

    def after_poll(self, context: PollLifecycleContext) -> None: ...


class NoopPollLifecycle:
    def before_poll(self, context: PollLifecycleContext) -> None:
        pass

    def after_poll(self, context: PollLifecycleContext) -> None:
        pass


class SftpDynamicCredentialLifecycle:
    def __init__(
        self,
        *,
        credential_provider: CredentialProvider,
        sftp_client: SFTPClient,
    ) -> None:
        self._credential_provider = credential_provider
        self._sftp_client = sftp_client

    def before_poll(self, context: PollLifecycleContext) -> None:
        credentials = self._credential_provider.get_credentials()

        self._sftp_client.configure_password(credentials)

    def after_poll(self, context: PollLifecycleContext) -> None:
        pass


class AapDynamicCredentialLifecycle:
    def __init__(
        self,
        *,
        credential_provider: CredentialProvider,
        aap_client: AAPClient,
    ) -> None:
        self._credential_provider = credential_provider
        self._aap_client = aap_client

    def before_poll(self, context: PollLifecycleContext) -> None:
        credentials = self._credential_provider.get_credentials()

        self._aap_client.configure_password(credentials)

    def after_poll(self, context: PollLifecycleContext) -> None:
        pass
