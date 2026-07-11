#!/usr/bin/env bash
# Safe deploy/.env loader — never executes shell words as commands.
#
# `source deploy/.env` breaks when a value contains spaces but is not quoted,
# e.g. DAEMON_EXEC_CMD=claude --dangerously-skip-permissions → bash tries to
# run `--dangerously-skip-permissions` as a command. This parser treats
# everything after the first `=` as the value (quoted or not).

load_deploy_env() {
  local env_file="${1:?env file path required}"

  if [ ! -f "$env_file" ]; then
    return 1
  fi

  local line key val
  while IFS= read -r line || [ -n "$line" ]; do
    # Strip inline comments only when `#` is preceded by whitespace.
    if [[ "$line" =~ ^([^#]*[^[:space:]#])[[:space:]]+# ]]; then
      line="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -z "$line" ] && continue

    if [[ ! "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      echo "load-env: ignoring invalid line in $env_file: $line" >&2
      continue
    fi

    key="${BASH_REMATCH[1]}"
    val="${BASH_REMATCH[2]}"

    if [[ "$val" =~ ^\"(.*)\"$ ]]; then
      val="${BASH_REMATCH[1]}"
    elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
      val="${BASH_REMATCH[1]}"
    fi

    export "$key=$val"
  done < "$env_file"
}
