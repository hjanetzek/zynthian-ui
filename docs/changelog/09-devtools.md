# Changelog: 09-devtools, developer tools

What strand 09 of `main` changes, newest entry first: `tools/` (test VM, QEMU VMs, syncing to
devices, profiling, screenshots) and its docs. File-disjoint from the code strands. Marker
`strand/09-devtools`; this file is the strand's last commit (see [README.md](README.md)).

## 2026-11-28: tools: switch_ui.sh testing (zynthian-ui-testing); zynctl.sh, the zynthian-operator client through uv

- `a83d6eeb7` switch_ui.sh: testing (zynthian-ui-testing, the testing branch)
- `2f02c818a` tools/zynctl.sh: the zynthian-operator client through uv

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-26: test VM: py3-jsonschema for upstream's zynseq schema tests

- `43c2b6626` test_vm.sh: py3-jsonschema for upstream's zynseq schema tests

## 2026-11-26: VM tools: clear errors for missing OpenGL and taken ports, run_qemu.sh -s grows a disk, zynthianos_vm.sh native rebuilds

- `800f45304` zynthianos_vm.sh: every run-tests mode rebuilds the native libraries first
- `1148344c9` VM tools: missing OpenGL and taken ports are clear errors
- `213639c85` run_qemu.sh: -s grows an existing, smaller disk

## 2026-11-21: VM tools: no firewall in the VMs, zynthianos_vm.sh sync/run-tests, qemu_compare.sh no longer upgrades on every start

- `4a59350a3` QEMU VMs: no firewall (nftables stopped and masked)
- `2c21ec12e` zynthianos_vm.sh: sync and restore write changed files with a new mtime and keep root ownership; run-tests native rebuilds
- `f65c1dbd0` qemu_compare.sh: setup waits for the VM's sshd before the key login check

## 2026-11-20: VMs forward the UI websocket

- `02ade2f5e` tools: forward the UI websocket (8370) of the QEMU VMs

## 2026-11-20: the strand when the changelog started

31 commits on strand 07, written 2026-11-03 to 2026-11-19.

- **Test suite VM:** `tools/test_vm.sh`, a QEMU VM that runs the test suite (never on the host)
  (`83ae1544b`, `1f28dab69`). Docs: [test-vm.md](../test-vm.md).
- **QEMU VMs:** run_qemu.sh, qemu_compare.sh (upstream's Tk UI and the Qt UI side by side), VM-to-VM
  LAN without root, a VM with upstream's own x86_64 ZynthianOS (`280742627`, `a57f0cc39`,
  `592f34acc`, `56302c260`, `6f5c86622`). Docs: [qemu-testing.md](../qemu-testing.md),
  [zynthianos-vm.md](../zynthianos-vm.md).
- **Devices:** sync_ui.sh (with -R: restart only the UI, checked; -q: QML only), switch_ui.sh,
  zyninject.sh, show_screen.py (`3c7f2b056`, `4aee87468`, `6f2e11557`, `3bf424577`, `42cc8cefc`,
  `44823e866`).
- **Measuring:** profiling and screenshot tools, screen_timing.py, display_bench.sh, Qt start-up
  (`233baba01`, `1fe76c0ac`, `790e84f35`, `3bbc91e4a`). Docs:
  [performance-measurement.md](../performance-measurement.md).
- **Other:** factory snapshot test, lv2_widget_designations.py, references to the Nura packaging in
  nura-builds (`03b65955f`, `91d7cc92a`, `fce89cd66`).
