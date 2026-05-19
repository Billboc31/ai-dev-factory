Both blocking issues resolved in a single commit:

1. **Dockerfile** — removed the Node.js + Claude CLI installation block (lines 17–23); the `runtime` stage now only installs `git`, `curl`, and Python deps.

2. **docker-compose.yml** — removed the `daemon` service entirely; Compose now defines only `api` and `web`. The plan V1 decision (daemon runs on the host) is preserved.

3. **deploy/env.example** — added an explicit comment block explaining how to start the daemon on the host with `AI_DEV_FACTORY_RUNTIME_ROOT` pointing at the Docker volume mount path.

4. **.pyc files** — `git rm --cached` on both `run_step.cpython-314.pyc` and `runtime_checkpoint.cpython-314.pyc`; they are now untracked and won't be versioned.
