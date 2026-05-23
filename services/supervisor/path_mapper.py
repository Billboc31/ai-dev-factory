"""Docker container-to-host path mapper for the supervisor.

The control API runs inside Docker and emits absolute paths that are valid
**inside the container** (`/app`, `/runtime/...`). The supervisor runs on
the host and must rewrite those paths to **host-side** equivalents before
spawning subprocesses (analysis/scripts/deploy workers).

Operators configure the mapping in ``deploy/.env`` — never hard-coded in
Python — using these variables:

::

    CONTAINER_PROJECT_ROOT=/app
    HOST_PROJECT_ROOT=/Users/<you>/runtime/ai-dev-factory/clones/ai-dev-factory

    CONTAINER_RUNTIME_ROOT=/runtime
    HOST_RUNTIME_ROOT=/Users/<you>/runtime/ai-dev-factory

The supervisor sources ``deploy/.env`` at startup (see
``deploy/start_supervisor.sh``) so both halves of the stack share a single
source of truth.

Matching priority
-----------------

When several rules could match the same path (e.g. ``/runtime`` is a
sub-path of nothing here but in principle two rules could compete), the
mapper picks the **longest container prefix that matches**. This avoids
ambiguous mappings such as ``/app`` accidentally absorbing
``/applications``.

If no rule matches, the original path is returned unchanged (identity).
A warning is logged so operators can spot misconfigurations easily.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("supervisor.path_mapper")


@dataclass(frozen=True)
class _MappingRule:
    name: str               # "project-root" or "runtime-root"
    container_prefix: str   # e.g. "/app"
    host_prefix: str        # e.g. "/Users/.../clones/ai-dev-factory"


class ContainerToHostMapper:
    """Rewrite container paths to host paths using env-driven rules.

    The mapper reads its rules from the process environment at instantiation
    time, so a fresh ``ContainerToHostMapper()`` after ``monkeypatch.setenv``
    or ``source deploy/.env`` always reflects the current configuration.
    """

    def __init__(self) -> None:
        self._rules: list[_MappingRule] = self._load_rules_from_env()
        if self._rules:
            for rule in self._rules:
                logger.info(
                    "path_mapper: rule loaded — %s: %r -> %r",
                    rule.name, rule.container_prefix, rule.host_prefix,
                )
        else:
            logger.warning(
                "path_mapper: no mapping rules configured "
                "(set CONTAINER_PROJECT_ROOT/HOST_PROJECT_ROOT, "
                "CONTAINER_RUNTIME_ROOT/HOST_RUNTIME_ROOT, and/or "
                "CONTAINER_SANDBOX_ROOT/HOST_SANDBOX_ROOT in deploy/.env). "
                "All paths will be returned unchanged."
            )

    @staticmethod
    def _load_rules_from_env() -> list[_MappingRule]:
        rules: list[_MappingRule] = []
        pairs = (
            ("project-root", "CONTAINER_PROJECT_ROOT", "HOST_PROJECT_ROOT"),
            ("runtime-root", "CONTAINER_RUNTIME_ROOT", "HOST_RUNTIME_ROOT"),
            ("sandbox-root", "CONTAINER_SANDBOX_ROOT", "HOST_SANDBOX_ROOT"),
        )
        for name, container_env, host_env in pairs:
            container = (os.environ.get(container_env) or "").strip()
            host = (os.environ.get(host_env) or "").strip()
            if container and host:
                # Strip trailing slashes to make prefix matching deterministic.
                rules.append(_MappingRule(
                    name=name,
                    container_prefix=container.rstrip("/") or container,
                    host_prefix=host.rstrip("/") or host,
                ))
        # Longest prefix wins on ambiguity. ``/applications`` must never be
        # captured by a ``/app`` rule because prefix is checked component-wise
        # (see ``_matches`` below), but sorting also matters when two
        # configured prefixes share a common ancestor.
        rules.sort(key=lambda r: len(r.container_prefix), reverse=True)
        return rules

    @staticmethod
    def _matches(path: str, prefix: str) -> bool:
        """Component-aware prefix match.

        ``/app`` matches ``/app`` and ``/app/foo`` but NOT ``/applications``.
        The check accepts the exact prefix, or the prefix followed by a
        path separator.
        """
        if path == prefix:
            return True
        return path.startswith(prefix + "/")

    def map(self, path: str) -> str:
        """Translate *path* from the container's view to the host's view.

        Returns the input unchanged when no rule matches or when no rules
        are configured. Each call logs the strategy used so operators can
        diagnose surprises from ``runs/daemon.log`` / ``analysis-*.log``.
        """
        if not path:
            return path
        for rule in self._rules:
            if self._matches(path, rule.container_prefix):
                mapped = rule.host_prefix + path[len(rule.container_prefix):]
                logger.info(
                    "path_mapper: mapped via %s: %r -> %r",
                    rule.name, path, mapped,
                )
                return mapped
        if self._rules:
            logger.info("path_mapper: no rule matched, identity: %r", path)
        return path
