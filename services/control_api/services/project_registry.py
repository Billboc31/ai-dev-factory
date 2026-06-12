from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from ..models.schemas import ProjectInfo

logger = logging.getLogger("control-api")

_WORKSPACE_FILENAME = "workspace.json"


@dataclass
class ProjectEntry:
    id: str
    root: Path


class ProjectRegistry:
    def __init__(
        self,
        projects_root: Path | None = None,
        _entries: list[ProjectEntry] | None = None,
        _workspace_file: Path | None = None,
    ) -> None:
        if _entries is not None:
            self._entries = _entries
        elif projects_root is not None:
            self._entries = self._scan(projects_root)
        else:
            raise ValueError("Either projects_root or _entries must be provided")
        self._workspace_file = _workspace_file

    @staticmethod
    def _scan(projects_root: Path) -> list[ProjectEntry]:
        entries: list[ProjectEntry] = []
        if not projects_root.is_dir():
            return entries
        for subdir in sorted(projects_root.iterdir()):
            if subdir.is_dir() and (subdir / ".git").is_dir():
                entries.append(ProjectEntry(id=subdir.name, root=subdir))
        return entries

    @classmethod
    def from_single_root(cls, root: Path) -> "ProjectRegistry":
        return cls(_entries=[ProjectEntry(id=root.name, root=root)])

    @classmethod
    def load_from_workspace_file(cls, runtime_root: Path) -> "ProjectRegistry":
        """Load the registry from ``{runtime_root}/workspace.json``.

        Falls back to an empty registry (no scan) when the file is absent or
        cannot be parsed.
        """
        workspace_file = runtime_root / _WORKSPACE_FILENAME
        entries: list[ProjectEntry] = []
        if workspace_file.exists():
            try:
                data = json.loads(workspace_file.read_text(encoding="utf-8"))
                for project_id, info in data.items():
                    root = Path(info["root"])
                    entries.append(ProjectEntry(id=project_id, root=root))
                logger.info(
                    "project_registry: loaded %d project(s) from %s",
                    len(entries), workspace_file,
                )
            except (json.JSONDecodeError, KeyError, OSError):
                logger.exception("project_registry: failed to load %s — starting empty", workspace_file)
        return cls(_entries=entries, _workspace_file=workspace_file)

    def _persist(self) -> None:
        if self._workspace_file is None:
            return
        data = {entry.id: {"root": str(entry.root)} for entry in self._entries}
        try:
            self._workspace_file.parent.mkdir(parents=True, exist_ok=True)
            self._workspace_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            logger.exception("project_registry: failed to persist %s", self._workspace_file)

    def ensure_registered(self, project_id: str, root: Path) -> bool:
        """Register *project_id* → *root* only if not already present.

        Returns True if a new entry was added, False if it already existed.
        Persists to workspace.json when a workspace file is configured.
        """
        for entry in self._entries:
            if entry.id == project_id:
                return False
        self._entries.append(ProjectEntry(id=project_id, root=root))
        self._persist()
        logger.info("project_registry: auto-registered project_id=%s root=%s", project_id, root)
        return True

    def register(self, project_id: str, root: Path) -> None:
        """Add *project_id* → *root* to the registry.

        Raises ``ValueError`` if the project_id is already registered.
        Persists to workspace.json when a workspace file is configured.
        """
        for entry in self._entries:
            if entry.id == project_id:
                raise ValueError(f"project_id already registered: {project_id!r}")
        self._entries.append(ProjectEntry(id=project_id, root=root))
        self._persist()
        logger.info("project_registry: registered project_id=%s root=%s", project_id, root)

    def unregister(self, project_id: str) -> None:
        """Remove *project_id* from the registry.

        Raises ``ValueError`` if the project_id is not registered.
        Persists to workspace.json when a workspace file is configured.
        """
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.id != project_id]
        if len(self._entries) == before:
            raise ValueError(f"project_id not registered: {project_id!r}")
        self._persist()
        logger.info("project_registry: unregistered project_id=%s", project_id)

    def list_projects(self, artifact_reader) -> list[ProjectInfo]:
        result: list[ProjectInfo] = []
        for entry in self._entries:
            try:
                tickets = artifact_reader.list_tickets(entry.root)
                tickets_count = len(tickets)
            except Exception:
                logger.exception("project_registry: failed to list tickets for %s", entry.root)
                tickets_count = 0
            result.append(ProjectInfo(
                name=entry.id,
                root=str(entry.root),
                tickets_count=tickets_count,
            ))
        return result

    def resolve(self, project_id: str) -> Path | None:
        for entry in self._entries:
            if entry.id == project_id:
                return entry.root
        return None
