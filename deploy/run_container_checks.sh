#!/usr/bin/env bash
# Usage: run_container_checks.sh IMAGE TAG_LABEL
# Runs the validation checks inside IMAGE (each with a timeout and a 1-CPU limit) and writes logs to
# logs/<TAG_LABEL>_*.log and container outputs to container_out/<TAG_LABEL>/.
set -u
IMAGE="$1"; L="$2"; shift 2
EXTRA_RUN_ARGS=("$@")             # e.g. extra docker run flags (none by default)
W=${PBTI_CHECK_DIR:-$(cd "$(dirname "$0")/.." && pwd)/results/containers}
LOG=$W/logs; OUT=$W/container_out/$L
mkdir -p "$LOG" "$OUT"; chmod 0777 "$OUT"   # world-writable so a non-root container user can write results
CPUS=1.0
run() {  # run NAME TIMEOUT_S CMD...
  local name="$1" to="$2"; shift 2
  local cname="pbti-check-$L-$name"
  {
    echo "# image: $IMAGE"; echo "# check: $name (timeout ${to}s, --cpus=$CPUS)"
    echo "# cmd: docker run --rm --cpus=$CPUS ${EXTRA_RUN_ARGS[*]} $*"
    echo "# start: $(date -u +%FT%TZ)"; local t0=$(date +%s.%N)
    timeout --signal=TERM "$to" docker run --rm --name "$cname" --cpus=$CPUS "${EXTRA_RUN_ARGS[@]}" "$@"
    local rc=$?
    if [ $rc -eq 124 ]; then echo "# TIMEOUT after ${to}s -> docker kill"; docker kill "$cname" >/dev/null 2>&1; fi
    local t1=$(date +%s.%N)
    echo "# exit_code: $rc"; echo "# end: $(date -u +%FT%TZ)"; echo "# wall_s: $(echo "$t1 - $t0" | bc)"
  } > "$LOG/${L}_$name.log" 2>&1
  echo "$name exit=$(grep '^# exit_code' "$LOG/${L}_$name.log" | awk '{print $3}')"
}
docker image inspect "$IMAGE" > "$LOG/${L}_image_inspect.json"
docker history --no-trunc "$IMAGE" > "$LOG/${L}_image_history.txt" 2>&1
run env 120 "$IMAGE" sh -c 'id; cat /etc/os-release | head -2; python3 --version; pip --version; pip freeze; mosquitto -h | head -1; make --version | head -1; pwd; ls -la'
run make_test 900 "$IMAGE" make test
run smoke 600 "$IMAGE" python3 -c "import sys; sys.path.insert(0,'src'); from pbti.scenarios import build; from pbti.oracle import evaluate; w=build('S01_normal','PBTI',1); w.run(); print(evaluate(w)['nonlegit_auth'], evaluate(w)['legit_missing'])"
run e2e 600 -v "$OUT:/out" "$IMAGE" python3 experiments/run_mqtt_e2e.py --rates 20 --reps 1 --warm 1 --measure 3 --drain 1 --out /out/mqtt_e2e_smoke.jsonl
echo "done $L"
