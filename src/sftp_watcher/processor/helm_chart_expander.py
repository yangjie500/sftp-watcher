import tarfile
from pathlib import Path
from posixpath import normpath

from sftp_watcher.processor.bundle_models import HelmChartExpansionResult


class PackagedHelmChartExpander:
    CHART_PACKAGE_SUFFIX = ".tgz"
    CHART_METADATA_FILENAME = "Chart.yaml"

    def expand(self, directory: Path) -> HelmChartExpansionResult:
        if not directory.exists():
            raise FileNotFoundError(
                f"Helm chart expansion directory does not exist: {directory}"
            )

        if not directory.is_dir():
            raise ValueError(
                f"Helm chart expansion path is not a directory: {directory}"
            )

        expanded_charts: list[Path] = []
        removed_packages: list[Path] = []

        for package_path in sorted(directory.rglob(f"*{self.CHART_PACKAGE_SUFFIX}")):
            if not package_path.is_file():
                continue

            chart_roots = self._extract_if_helm_chart_package(package_path)
            if not chart_roots:
                continue

            package_path.unlink()
            expanded_charts.extend(chart_roots)
            removed_packages.append(package_path)

        return HelmChartExpansionResult(
            expanded_charts=tuple(expanded_charts),
            removed_packages=tuple(removed_packages),
        )

    def _extract_if_helm_chart_package(self, package_path: Path) -> tuple[Path, ...]:
        try:
            with tarfile.open(package_path, mode="r:*") as tar:
                members = tar.getmembers()

                chart_roots = self._chart_roots(
                    package_path=package_path,
                    members=members,
                )
                if not chart_roots:
                    return ()

                for member in members:
                    target_path = package_path.parent / member.name

                    if not self._is_safe_path(package_path.parent, target_path):
                        raise ValueError(
                            f"Unsafe path detected in Helm chart package: {member.name}"
                        )

                tar.extractall(package_path.parent, filter="data")

        except tarfile.TarError:
            return ()

        return chart_roots

    def _chart_roots(
        self,
        *,
        package_path: Path,
        members: list[tarfile.TarInfo],
    ) -> tuple[Path, ...]:
        chart_roots: list[Path] = []

        for member in members:
            normalized_name = normpath(member.name)

            if normalized_name == ".":
                continue

            path = Path(normalized_name)
            if path.name != self.CHART_METADATA_FILENAME:
                continue

            chart_root = package_path.parent / path.parent
            if chart_root not in chart_roots:
                chart_roots.append(chart_root)

        return tuple(chart_roots)

    def _is_safe_path(self, base_dir: Path, target_path: Path) -> bool:
        base_dir = base_dir.resolve()
        target_path = target_path.resolve()

        return base_dir == target_path or base_dir in target_path.parents
