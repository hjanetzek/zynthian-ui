# Changelog: 06-loadopt, load and start-up time

What strand 06 of `main` changes, newest entry first: faster snapshot loads, engine stops and UI
start-up. Needs strands 03 and 05. Marker `strand/06-loadopt`; this file is the strand's last
commit (see [README.md](README.md)).

## 2026-11-20: rebased onto tomita 0c1098a68: remove_all_chains() refreshes upstream's CC feedback broker (d6d08865) once at its end, like the deferred automation check; see rebase-onto-tomita-2026-11-20c.md

- `45cf83069` Chain manager: remove_all_chains does the per-chain work once

## 2026-11-20: strand 01's start-failure fixes below: the crashed-jalv logging commit no longer adds the output thread's stop (now in 01), only the exit status log

- `0dee54f4d` jalv engine: log how crashed or hung jalvs ended; no spinning on a dead jalv

## 2026-11-20: Tests robust in upstream's CI: geomspace compared with numpy to rounding

- `7296c202a` tests: geomspace compared with numpy to rounding (numpy versions differ in the last bit)

## 2026-11-20: Tests robust in upstream's CI: the TTL info test skips where rdflib is stubbed

- `0414314af` tests: TTL info test skips where rdflib is stubbed

## 2026-11-20: the strand when the changelog started

26 commits on strand 05, written 2026-11-17 to 2026-11-18.

- **jalv:** started with the plugin's bundles only (`jalv -B`, also jalv.gtk3), with a fallback,
  logged warnings and how crashed or hung jalvs ended (`24b40c6cc`, `daf9dec4d`, `eca69fda4`,
  `7d8b02279`, `0dee54f4d`).
- **Engine stops:** in parallel, processes reaped with bounded timeouts, sfizz and Pure Data
  stopped before a load, sfizz and pexpect timings shortened, slow stops logged (`054b263f8`,
  `70a9caba7`, `16aa9bce3`, `07541dbfc`, `8e20d181a`, `1a23b6b93`).
- **Less work per load:** remove_all_chains once, events instead of polling, the LV2 port
  description cached per plugin (`45cf83069`, `0212e1cc1`, `9e76a4a21`).
- **Start-up:** the lilv world built on first use, lazy imports (numpy, requests, rdflib), LV2 data
  loaded in the background after start-up, a lighter jackd scan (`172bdb6db`, `25f5bf28b`,
  `0ef616182`, `78de1de6a`, `3b2282fb3`, `dc26fba18`).
- **Engine output drained:** engines on a pty read all the time; VLC's output to /dev/null;
  alsa_in/alsa_out drained (`d5640edb8`, `efe70babd`, `098fc3f18`). Docs:
  [performance-measurement.md](../performance-measurement.md).
