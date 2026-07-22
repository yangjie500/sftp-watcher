import logging
import time
from pathlib import Path
from typing import Any

from sftp_watcher.config import AAPConfig, SFTPWatcherConfig
from sftp_watcher.credentials import (
    CyberArkCCPCredentialProvider,
    FromConfigCredentialProvider,
)
from sftp_watcher.lifecycles.lifecycle import (
    AapDynamicCredentialLifecycle,
    PollLifecycle,
    SftpDynamicCredentialLifecycle,
)
from sftp_watcher.lifecycles.local_file_cleanup import LocalFileCleanupLifecycle
from sftp_watcher.processor.action.aap_client import AAPClient
from sftp_watcher.processor.processor import FileProcessorRouter
from sftp_watcher.processor.tarball_processor import TarballProcessor
from sftp_watcher.sftp_client import ParamikoSFTPClient, SFTPClient
from sftp_watcher.sftp_watcher import SFTPWatcher
from sftp_watcher.state_store import (
    DownloadStateService,
    SQLiteDownloadRecordRepository,
)
from sftp_watcher.telemetry import configure_observability

logger = logging.getLogger(__name__)


def start_application(env_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    sftp_config = SFTPWatcherConfig.from_env(env_file)
    aap_config = AAPConfig.from_env(env_file)

    observability = configure_observability()

    sftp_credential_provider = _build_credential_provider(
        config=sftp_config,
        config_credential_key="password",
        credential_name="SFTP password",
    )

    aap_credential_provider = _build_credential_provider(
        config=aap_config,
        config_credential_key="token",
        credential_name="AAP token",
    )

    sftp_client: SFTPClient = ParamikoSFTPClient(
        host=sftp_config.host,
        port=sftp_config.port,
        username=sftp_config.username,
        password=sftp_config.password,
    )

    repository = SQLiteDownloadRecordRepository(
        local_dir=sftp_config.state_store_dir,
    )

    state_service = DownloadStateService(repository)

    aap_client = AAPClient(aap_config)

    processor_router = FileProcessorRouter(
        processors=[
            TarballProcessor(
                job_template_launcher=aap_client,
            ),
        ]
    )

    fetch_sftp_credential_lifecycle: PollLifecycle = SftpDynamicCredentialLifecycle(
        credential_provider=sftp_credential_provider,
        sftp_client=sftp_client,
    )

    fetch_aap_credential_lifecycle: PollLifecycle = AapDynamicCredentialLifecycle(
        credential_provider=aap_credential_provider,
        aap_client=aap_client,
    )

    cleanup_lifecycle: PollLifecycle = LocalFileCleanupLifecycle(
        local_dir=sftp_config.local_dir,
        retention_days=sftp_config.local_file_retention_days,
        enabled=sftp_config.cleanup_local_files_enabled,
    )

    watcher = SFTPWatcher(
        sftp_client=sftp_client,
        state_service=state_service,
        processor_router=processor_router,
        config=sftp_config,
        lifecycles=[
            fetch_sftp_credential_lifecycle,
            fetch_aap_credential_lifecycle,
            cleanup_lifecycle,
        ],
    )

    logger.info("Starting SFTP watcher application")

    try:
        while True:
            try:
                watcher.poll_once()
            except Exception:
                logger.exception("SFTP watcher poll failed; continuing")

            time.sleep(sftp_config.poll_interval_seconds)

    except KeyboardInterrupt:
        logger.info("SFTP watcher application stopped by user")

    finally:
        repository.close()
        observability.shutdown()


def _build_credential_provider(
    *,
    config: Any,
    config_credential_key: str,
    credential_name: str,
):
    if config.credential_source == "config":
        return FromConfigCredentialProvider(
            config=config,
            password_key=config_credential_key,
        )

    if config.credential_source == "cyberark_ccp":
        if config.cyberark_ccp is None:
            raise ValueError(f"{credential_name} CyberArk CCP config is required")

        return CyberArkCCPCredentialProvider(
            config.cyberark_ccp, credential_name=credential_name
        )

    raise ValueError(
        f"Unsupported credential source for {credential_name}: "
        f"{config.credential_source}"
    )
