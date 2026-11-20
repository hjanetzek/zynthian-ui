# Changelog: 09-devtools, developer tools

What strand 09 of `main` changes, newest entry first: `tools/` (test VM, QEMU VMs, syncing to
devices, profiling, screenshots) and its docs. File-disjoint from the code strands. Marker
`strand/09-devtools`; this file is the strand's last commit (see [README.md](README.md)).

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-26: test VM: py3-jsonschema for upstream's zynseq schema tests

- `6aeab2810` test_vm.sh: py3-jsonschema for upstream's zynseq schema tests

## 2026-11-26: VM tools: clear errors for missing OpenGL and taken ports, run_qemu.sh -s grows a disk, zynthianos_vm.sh native rebuilds

- `05ddbe2b5` zynthianos_vm.sh: every run-tests mode rebuilds the native libraries first
- `493311aa6` VM tools: missing OpenGL and taken ports are clear errors
- `1c1c96d39` run_qemu.sh: -s grows an existing, smaller disk

## 2026-11-21: VM tools: no firewall in the VMs, zynthianos_vm.sh sync/run-tests, qemu_compare.sh no longer upgrades on every start

- `823a78a0c` QEMU VMs: no firewall (nftables stopped and masked)
- `3aeaf02f6` zynthianos_vm.sh: sync and restore write changed files with a new mtime and keep root ownership; run-tests native rebuilds
- `b0dc456cd` qemu_compare.sh: setup waits for the VM's sshd before the key login check

## 2026-11-20: VMs forward the UI websocket

- `ba1386278` tools: forward the UI websocket (8370) of the QEMU VMs

## 2026-11-20: the strand when the changelog started

31 commits on strand 07, written 2026-11-03 to 2026-11-19.

- **Test suite VM:** `tools/test_vm.sh`, a QEMU VM that runs the test suite (never on the host)
  (`e276acf4d`, `fd7016a1f`). Docs: [test-vm.md](../test-vm.md).
- **QEMU VMs:** run_qemu.sh, qemu_compare.sh (upstream's Tk UI and the Qt UI side by side), VM-to-VM
  LAN without root, a VM with upstream's own x86_64 ZynthianOS (`da6880892`, `cee4eb330`,
  `122c31205`, `cdf86b6e4`, `8d9b20c8d`). Docs: [qemu-testing.md](../qemu-testing.md),
  [zynthianos-vm.md](../zynthianos-vm.md).
- **Devices:** sync_ui.sh (with -R: restart only the UI, checked; -q: QML only), switch_ui.sh,
  zyninject.sh, show_screen.py (`6e9321f7a`, `3645c05cd`, `10196b656`, `593cb084f`, `67394dde2`,
  `760954823`).
- **Measuring:** profiling and screenshot tools, screen_timing.py, display_bench.sh, Qt start-up
  (`d5a0e916f`, `325a80e73`, `95fc3b45b`, `1f81735e9`). Docs:
  [performance-measurement.md](../performance-measurement.md).
- **Other:** factory snapshot test, lv2_widget_designations.py, references to the Nura packaging in
  nura-builds (`c84595281`, `44a9b8702`, `0026b2ad8`).
