from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..models.schemas import ProjectInfo

logger = logging.getLogger("control-api")


@dataclass
class ProjectEntry:
    id: str
    root: Path


class ProjectRegistry:
    def __init__(
        self,
        projects_root: Path | None = None,
        _entries: list[ProjectEntry] | None = None,
    ) -> None:
        if _entries is not None:
            self._entries = _entries
        elif projects_root is not None:
            self._entries = self._scan(projects_root)
        else:
            raise ValueError("Either projects_root or _entries must be provided")

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
