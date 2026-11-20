# Changelog: 06-loadopt, load and start-up time

What strand 06 of `main` changes, newest entry first: faster snapshot loads, engine stops and UI
start-up. Needs strands 03 and 05. Marker `strand/06-loadopt`; this file is the strand's last
commit (see [README.md](README.md)).

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-21: jalv's output thread after jalv's end: tests for a crash mid-line, a pipe kept open, proc_cmd()'s restart

- `a8a6bec48` tests: jalv's output thread after jalv's end: crash mid-line, open pipe, restart

## 2026-11-20: rebased onto tomita 0c1098a68: remove_all_chains() refreshes upstream's CC feedback broker (d6d08865) once at its end, like the deferred automation check; see rebase-onto-tomita-2026-11-20c.md

- `e8db1e416` Chain manager: remove_all_chains does the per-chain work once

## 2026-11-20: strand 01's start-failure fixes below: the crashed-jalv logging commit no longer adds the output thread's stop (now in 01), only the exit status log

- `98a08413a` jalv engine: log how crashed or hung jalvs ended; no spinning on a dead jalv

## 2026-11-20: Tests robust in upstream's CI: geomspace compared with numpy to rounding

- `ce6fdf595` tests: geomspace compared with numpy to rounding (numpy versions differ in the last bit)

## 2026-11-20: Tests robust in upstream's CI: the TTL info test skips where rdflib is stubbed

- `b77a99177` tests: TTL info test skips where rdflib is stubbed

## 2026-11-20: the strand when the changelog started

26 commits on strand 05, written 2026-11-17 to 2026-11-18.

- **jalv:** started with the plugin's bundles only (`jalv -B`, also jalv.gtk3), with a fallback,
  logged warnings and how crashed or hung jalvs ended (`dd042f1c5`, `f5f688369`, `b5293db3e`,
  `ccdc5e4fd`, `98a08413a`).
- **Engine stops:** in parallel, processes reaped with bounded timeouts, sfizz and Pure Data
  stopped before a load, sfizz and pexpect timings shortened, slow stops logged (`cb25a69e8`,
  `9e7ccc96b`, `3a82a6061`, `a7d52494a`, `ae49b9da8`, `85bed68c3`).
- **Less work per load:** remove_all_chains once, events instead of polling, the LV2 port
  description cached per plugin (`e8db1e416`, `4d00e1394`, `827222576`).
- **Start-up:** the lilv world built on first use, lazy imports (numpy, requests, rdflib), LV2 data
  loaded in the background after start-up, a lighter jackd scan (`9382b8127`, `8314c67e8`,
  `739d2f41d`, `60609dbb0`, `2dba86589`, `4d8895e66`).
- **Engine output drained:** engines on a pty read all the time; VLC's output to /dev/null;
  alsa_in/alsa_out drained (`470d3e336`, `5bd96a314`, `cb040b2f4`). Docs:
  [performance-measurement.md](../performance-measurement.md).
