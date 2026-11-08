#!/usr/bin/env bash
# Extra runtime checks (all with timeouts, 1 CPU max):
#   shutdown <image> <label>   : start the image's default CMD detached, `docker stop -t 20` after 8 s, time it
#   health   <image> <label>   : run with a fast health interval and read .State.Health
#   hardened <image> <label>   : smoke + e2e under --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges
#   e2e_again <image> <label> <n> : repeat the unchanged e2e smoke n times (race characterisation)
set -u
W=${PBTI_CHECK_DIR:-$(cd "$(dirname "$0")/.." && pwd)/results/containers}; LOG=$W/logs
mode="$1"; IMAGE="$2"; L="$3"
case "$mode" in
shutdown)
  c="pbti-stop-$L"; f="$LOG/${L}_shutdown.log"
  {
    echo "# image: $IMAGE  default ENTRYPOINT/CMD, detached, --cpus=1.0"; echo "# start: $(date -u +%FT%TZ)"
    docker rm -f "$c" >/dev/null 2>&1
    docker run -d --name "$c" --cpus=1.0 "$IMAGE" >/dev/null
    sleep 8
    echo "# processes before stop:"; docker top "$c" -eo pid,ppid,user,args 2>&1 | cut -c1-150
    t0=$(date +%s.%N); timeout 60 docker stop -t 20 "$c" >/dev/null; t1=$(date +%s.%N)
    echo "# docker stop -t 20 took: $(echo "$t1 - $t0" | bc) s"
    echo "# state: $(docker inspect -f 'ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} Error={{.State.Error}}' "$c")"
    echo "# container log tail:"; docker logs --tail 15 "$c" 2>&1
    docker rm -f "$c" >/dev/null 2>&1; echo "# end: $(date -u +%FT%TZ)"
  } > "$f" 2>&1; grep -E "took|state" "$f";;
health)
  c="pbti-health-$L"; f="$LOG/${L}_healthcheck.log"
  {
    echo "# image: $IMAGE"; echo "# configured: $(docker image inspect -f '{{json .Config.Healthcheck}}' "$IMAGE")"
    docker rm -f "$c" >/dev/null 2>&1
    echo "# cmd: docker run -d --cpus=0.5 --health-interval=5s --health-start-period=0s --health-retries=1 $IMAGE sleep 60"
    docker run -d --name "$c" --cpus=0.5 --health-interval=5s --health-start-period=0s --health-retries=1 "$IMAGE" sleep 60 >/dev/null
    for i in 1 2 3 4; do sleep 5; echo "# t+$((i*5))s status: $(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$c")"; done
    echo "# last probe: $(docker inspect -f '{{if .State.Health}}{{json (index .State.Health.Log 0)}}{{end}}' "$c")"
    docker rm -f "$c" >/dev/null 2>&1
  } > "$f" 2>&1; grep -E "status" "$f" | tail -1;;
hardened)
  OUT=$W/container_out/${L}_hardened; mkdir -p "$OUT"; chmod 0777 "$OUT"
  H=(--read-only --tmpfs /tmp:rw,exec,size=256m --cap-drop ALL --security-opt no-new-privileges --cpus=1.0)
  for chk in smoke e2e; do
    f="$LOG/${L}_hardened_$chk.log"; c="pbti-hard-$L-$chk"
    if [ $chk = smoke ]; then CMD=(python3 -c "import sys; sys.path.insert(0,'src'); from pbti.scenarios import build; from pbti.oracle import evaluate; w=build('S01_normal','PBTI',1); w.run(); print(evaluate(w)['nonlegit_auth'], evaluate(w)['legit_missing'])"); V=();
    else CMD=(python3 experiments/run_mqtt_e2e.py --rates 20 --reps 1 --warm 1 --measure 3 --drain 1 --out /out/mqtt_e2e_smoke.jsonl); V=(-v "$OUT:/out"); fi
    {
      echo "# image: $IMAGE  hardened runtime: ${H[*]}"; echo "# cmd: ${CMD[*]}"; echo "# start: $(date -u +%FT%TZ)"
      timeout 600 docker run --rm --name "$c" "${H[@]}" "${V[@]}" "$IMAGE" "${CMD[@]}"; rc=$?
      [ $rc -eq 124 ] && docker kill "$c" >/dev/null 2>&1
      echo "# exit_code: $rc"; echo "# end: $(date -u +%FT%TZ)"
    } > "$f" 2>&1; echo "$chk exit=$(grep '^# exit_code' "$f" | awk '{print $3}')"
  done;;
e2e_again)
  n="$4"
  for i in $(seq 1 "$n"); do
    OUT=$W/container_out/${L}_e2e_repeat$i; mkdir -p "$OUT"; chmod 0777 "$OUT"; f="$LOG/${L}_e2e_repeat$i.log"; c="pbti-e2e-$L-$i"
    {
      echo "# image: $IMAGE  repeat $i of the unchanged e2e smoke"; echo "# start: $(date -u +%FT%TZ)"
      timeout 600 docker run --rm --name "$c" --cpus=1.0 -v "$OUT:/out" "$IMAGE" python3 experiments/run_mqtt_e2e.py --rates 20 --reps 1 --warm 1 --measure 3 --drain 1 --out /out/mqtt_e2e_smoke.jsonl; rc=$?
      [ $rc -eq 124 ] && docker kill "$c" >/dev/null 2>&1
      echo "# exit_code: $rc"; echo "# end: $(date -u +%FT%TZ)"
    } > "$f" 2>&1; echo "repeat $i: $(grep -c 'rep 1 rate 20' "$f") system lines, $(grep -c 'nan ms' "$f") nan, $(grep -c Traceback "$f") tracebacks"
  done;;
esac
