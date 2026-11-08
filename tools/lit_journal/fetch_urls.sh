#!/usr/bin/env bash
# Usage: fetch_urls.sh <list.tsv: key<TAB>url> <outdir>
# Downloads each URL with plain curl (default user agent) into <outdir>/<key>/ and prints status lines.
list="$1"; out="$2"
while IFS=$'\t' read -r key url; do
  [ -z "$key" ] && continue
  mkdir -p "$out/$key"
  res=$(curl -sS -L --max-time 60 -o "$out/$key/body" -w '%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}' "$url" 2>&1)
  printf '%s\t%s\t%s\n' "$key" "$url" "$res"
  sleep 0.5
done < "$list"
