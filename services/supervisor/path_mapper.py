"""Docker container-to-host path mapper for the supervisor."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("supervisor.path_mapper")


class ContainerToHostMapper:
    def __init__(self) -> None:
        self.container_root = os.environ.get("CONTAINER_RUNTIME_ROOT", "")
        self.host_root = os.environ.get("HOST_RUNTIME_ROOT", "")

    def map(self, path: str) -> str:
        if not self.container_root or not self.host_root:
            return path
        if path == self.container_root or path.startswith(self.container_root + "/"):
            mapped = self.host_root + path[len(self.container_root):]
            logger.info("path_mapper: %r -> %r", path, mapped)
            return mapped
        return path
