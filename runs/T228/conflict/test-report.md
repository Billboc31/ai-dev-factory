# Test Report — conflict resolution for T228
Generated at: 2026-08-06T07:14:28Z
Exit code: 2

## Output


==================================== ERRORS ====================================
________________ ERROR collecting tests/test_container_paths.py ________________
ImportError while importing test module '/Users/pierrebocquet/runtime/ai-dev-factory/worktrees/T228/tests/test_container_paths.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_container_paths.py:10: in <module>
    from control_api.services.container_paths import to_container_path
E   ModuleNotFoundError: No module named 'control_api.services'
_______________ ERROR collecting tests/test_ihm_worktree_cwd.py ________________
ImportError while importing test module '/Users/pierrebocquet/runtime/ai-dev-factory/worktrees/T228/tests/test_ihm_worktree_cwd.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ihm_worktree_cwd.py:14: in <module>
    from control_api.services.subprocess_runner import (
E   ModuleNotFoundError: No module named 'control_api.services'
_______________ ERROR collecting tests/test_runtime_resolver.py ________________
ImportError while importing test module '/Users/pierrebocquet/runtime/ai-dev-factory/worktrees/T228/tests/test_runtime_resolver.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_runtime_resolver.py:9: in <module>
    from control_api.services.runtime_resolver import resolve_ticket_run_dir, resolve_ticket_cwd
E   ModuleNotFoundError: No module named 'control_api.services'
=============================== warnings summary ===============================
tests/test_healthcheck_classification.py:16
  /Users/pierrebocquet/runtime/ai-dev-factory/worktrees/T228/tests/test_healthcheck_classification.py:16: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR tests/test_container_paths.py
ERROR tests/test_ihm_worktree_cwd.py
ERROR tests/test_runtime_resolver.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 3 errors in 2.28s

