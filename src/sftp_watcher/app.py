import logging
import time
from pathlib import Path
from typing import Any

from sftp_watcher.bundle.content_filter import (
    ContainerImageRemovingBundleContentFilter,
)
from sftp_watcher.bundle.extractor import SafeTarBundleExtractor
from sftp_watcher.bundle.helm_chart_expander import PackagedHelmChartExpander
from sftp_watcher.bundle.release_manifest_writer import ReleaseManifestWriter
from sftp_watcher.config import AppConfig
from sftp_watcher.credentials import (
    CyberArkCCPCredentialProvider,
    FromConfigCredentialProvider,
)
from sftp_watcher.handler.git_command_runner import GitCommandRunner
from sftp_watcher.handler.git_prepared_bundle_handler import (
    GitPreparedBundleHandler,
)
from sftp_watcher.handler.git_publish_target import (
    MappingGitPublishTargetResolver,
    TemplateGitPublishBranchResolver,
)
from sftp_watcher.lifecycles.lifecycle import (
    PollLifecycle,
    SftpDynamicCredentialLifecycle,
)
from sftp_watcher.lifecycles.local_file_cleanup import LocalFileCleanupLifecycle
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
    app_config = AppConfig.from_env(env_file)
    sftp_config = app_config.sftp
    git_config = app_config.git
    bundle_config = app_config.bundle

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [console_handler]

    if sftp_config.log_file is not None:
        sftp_config.log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(sftp_config.log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)

    observability = configure_observability(
        enabled=sftp_config.telemetry_enabled,
        verify_tls=sftp_config.telemetry_verify_tls,
    )

    sftp_credential_provider = _build_credential_provider(
        config=sftp_config,
        config_credential_key="password",
        credential_name="SFTP password",
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

    git_runner = GitCommandRunner(
        timeout_seconds=git_config.timeout_seconds,
        secrets=(git_config.password,) if git_config.password is not None else (),
    )
    publish_target_resolver = MappingGitPublishTargetResolver(
        tenant_remote_urls=git_config.tenant_remote_urls or {},
        default_branch=git_config.branch,
        fallback_remote_url=git_config.remote_url,
    )
    publish_branch_resolver = TemplateGitPublishBranchResolver(
        branch_template=git_config.branch_template,
    )
    bundle_handler = GitPreparedBundleHandler(
        config=git_config,
        publish_target_resolver=publish_target_resolver,
        publish_branch_resolver=publish_branch_resolver,
        git_runner=git_runner,
    )

    processor_router = FileProcessorRouter(
        processors=[
            TarballProcessor(
                bundle_extractor=SafeTarBundleExtractor(),
                content_filter=ContainerImageRemovingBundleContentFilter(
                    container_image_dirs=bundle_config.container_image_dirs,
                ),
                helm_chart_expander=PackagedHelmChartExpander(),
                bundle_handler=bundle_handler,
                release_manifest_writer=ReleaseManifestWriter(),
                filename_metadata_separator=bundle_config.filename_metadata_separator,
            ),
        ]
    )

    fetch_sftp_credential_lifecycle: PollLifecycle = SftpDynamicCredentialLifecycle(
        credential_provider=sftp_credential_provider,
        sftp_client=sftp_client,
    )

    cleanup_lifecycle: PollLifecycle = LocalFileCleanupLifecycle(
        local_dir=sftp_config.local_dir,
        retention_days=sftp_config.local_file_retention_days,
        cleanup_interval_seconds=sftp_config.cleanup_interval_seconds,
        enabled=sftp_config.cleanup_local_files_enabled,
    )

    watcher = SFTPWatcher(
        sftp_client=sftp_client,
        state_service=state_service,
        processor_router=processor_router,
        config=sftp_config,
        lifecycles=[
            fetch_sftp_credential_lifecycle,
            cleanup_lifecycle,
        ],
        filename_metadata_separator=bundle_config.filename_metadata_separator,
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
