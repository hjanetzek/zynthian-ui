# Changelog: 09-devtools, developer tools

What strand 09 of `main` changes, newest entry first: `tools/` (test VM, QEMU VMs, syncing to
devices, profiling, screenshots) and its docs. File-disjoint from the code strands. Marker
`strand/09-devtools`; this file is the strand's last commit (see [README.md](README.md)).

## 2026-11-20: VMs forward the UI websocket

- `6301d523c` tools: forward the UI websocket (8370) of the QEMU VMs

## 2026-11-20: the strand when the changelog started

31 commits on strand 07, written 2026-11-03 to 2026-11-19.

- **Test suite VM:** `tools/test_vm.sh`, a QEMU VM that runs the test suite (never on the host)
  (`17497b23c`, `6bb691af6`). Docs: [test-vm.md](../test-vm.md).
- **QEMU VMs:** run_qemu.sh, qemu_compare.sh (upstream's Tk UI and the Qt UI side by side), VM-to-VM
  LAN without root, a VM with upstream's own x86_64 ZynthianOS (`0536eb372`, `c5e3b1a94`,
  `7bc0ab59b`, `9d1f594dd`, `8aff4384f`). Docs: [qemu-testing.md](../qemu-testing.md),
  [zynthianos-vm.md](../zynthianos-vm.md).
- **Devices:** sync_ui.sh (with -R: restart only the UI, checked; -q: QML only), switch_ui.sh,
  zyninject.sh, show_screen.py (`e6226c8d8`, `344c8e920`, `eb88080ad`, `17f7de4b4`, `d743d0376`,
  `640093f07`).
- **Measuring:** profiling and screenshot tools, screen_timing.py, display_bench.sh, Qt start-up
  (`0d234cd51`, `80a84169d`, `9658ee8ca`, `56abbed23`). Docs:
  [performance-measurement.md](../performance-measurement.md).
- **Other:** factory snapshot test, lv2_widget_designations.py, references to the Nura packaging in
  nura-builds (`31f8e9328`, `9eabf0857`, `c8d285425`).
