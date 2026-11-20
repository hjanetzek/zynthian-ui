# Changelog: 06-loadopt, load and start-up time

What strand 06 of `main` changes, newest entry first: faster snapshot loads, engine stops and UI
start-up. Needs strands 03 and 05. Marker `strand/06-loadopt`; this file is the strand's last
commit (see [README.md](README.md)).

## 2026-11-28: rebased onto tomita 046817e4: conflicts in the autoconnect polling and engine stop commits (imports next to upstream's main-loop lock); see rebase-onto-tomita-2026-11-28.md

## 2026-11-27: rebased onto tomita 5b0b6966: conflict in the lazy lilv world (upstream's LV2 scan speed-ups 5f4a18c4, c391277b: rdflib import, preset workaround removed), see rebase-onto-tomita-2026-11-27.md

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-21: jalv's output thread after jalv's end: tests for a crash mid-line, a pipe kept open, proc_cmd()'s restart

- `a022d0e7e` tests: jalv's output thread after jalv's end: crash mid-line, open pipe, restart

## 2026-11-20: rebased onto tomita 0c1098a68: remove_all_chains() refreshes upstream's CC feedback broker (d6d08865) once at its end, like the deferred automation check; see rebase-onto-tomita-2026-11-20c.md

- `b91adb401` Chain manager: remove_all_chains does the per-chain work once

## 2026-11-20: strand 01's start-failure fixes below: the crashed-jalv logging commit no longer adds the output thread's stop (now in 01), only the exit status log

- `0e3ac92ae` jalv engine: log how crashed or hung jalvs ended; no spinning on a dead jalv

## 2026-11-20: Tests robust in upstream's CI: geomspace compared with numpy to rounding

- `bbdb40fe8` tests: geomspace compared with numpy to rounding (numpy versions differ in the last bit)

## 2026-11-20: Tests robust in upstream's CI: the TTL info test skips where rdflib is stubbed

- `f61993ebd` tests: TTL info test skips where rdflib is stubbed

## 2026-11-20: the strand when the changelog started

26 commits on strand 05, written 2026-11-17 to 2026-11-18.

- **jalv:** started with the plugin's bundles only (`jalv -B`, also jalv.gtk3), with a fallback,
  logged warnings and how crashed or hung jalvs ended (`25bbe97d9`, `8549fd3a4`, `a871ad16a`,
  `1c48cdcc9`, `0e3ac92ae`).
- **Engine stops:** in parallel, processes reaped with bounded timeouts, sfizz and Pure Data
  stopped before a load, sfizz and pexpect timings shortened, slow stops logged (`8e2bd7242`,
  `f966f7a21`, `ffa3fad2a`, `2c3bf4fb3`, `a445bb6cf`, `83df97f93`).
- **Less work per load:** remove_all_chains once, events instead of polling, the LV2 port
  description cached per plugin (`b91adb401`, `e5b6b14e0`, `8d6a95396`).
- **Start-up:** the lilv world built on first use, lazy imports (numpy, requests, rdflib), LV2 data
  loaded in the background after start-up, a lighter jackd scan (`add26dbcc`, `e79ceec93`,
  `b8aa4c82d`, `eb299051d`, `f196790b7`, `7dae262cf`).
- **Engine output drained:** engines on a pty read all the time; VLC's output to /dev/null;
  alsa_in/alsa_out drained (`b657d37b7`, `0903b8f2f`, `2a54105bb`). Docs:
  [performance-measurement.md](../performance-measurement.md).
