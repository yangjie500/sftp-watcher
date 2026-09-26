from dataclasses import dataclass
from pathlib import Path

from sftp_watcher.config.bundle import BundleProcessingConfig
from sftp_watcher.config.git import GitPublisherConfig
from sftp_watcher.config.sftp import SFTPWatcherConfig
from sftp_watcher.config.utils import load_environment


@dataclass(frozen=True)
class AppConfig:
    sftp: SFTPWatcherConfig
    git: GitPublisherConfig
    bundle: BundleProcessingConfig

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "AppConfig":
        load_environment(env_file)

        return cls(
            sftp=SFTPWatcherConfig.from_env(),
            git=GitPublisherConfig.from_env(),
            bundle=BundleProcessingConfig.from_env(),
        )
