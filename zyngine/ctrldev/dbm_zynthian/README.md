# DrivenByMoss on Zynthian

zynthian controller drivers (ctrldev) which run DrivenByMoss controllers on zynthian: the core runs
the controller, zynthian is its DAW.

The drivers live in zynthian-ui (moved from `backends/zynthian` of
[drivenbymoss-rust](https://github.com/hjanetzek/drivenbymoss-rust) on 2026-11-25, with their
history). The core (the native library `libdrivenbymoss.so`), its Python binding `drivenbymoss`,
the reference host `dbm_host` and the protocol
([doc/TYPED_PROTOCOL_PLAN.md](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/TYPED_PROTOCOL_PLAN.md)) stay in drivenbymoss-rust and come
from the drivenbymoss package. Plan and state: [doc/ZYNTHIAN_PLAN.md](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_PLAN.md),
analysis: [doc/ZYNTHIAN_INTEGRATION.md](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_INTEGRATION.md) (both in drivenbymoss-rust);
here: [docs/dbm/](../../../docs/dbm/) (the window indication analysis, the CPU profile).

## Layout

| Path | Content |
| --- | --- |
| `zyngine/ctrldev/` | The driver base `zynthian_ctrldev_base_dbm.py`, one module per controller (`zynthian_ctrldev_dbm_*.py`), the model adapter package `dbm_zynthian/` (this folder) |
| `tests/dbm/` | The tests without the zynthian UI (`run_tests.py`), the conformance scenarios against the adapter (`zyn_conformance.py`) |
| `docs/dbm/` | Analyses: `ZYNTHIAN_INDICATION.md`, `ZYNTHIAN_CPU.md` |

## Finding DrivenByMoss

`dbm_zynthian.import_dbm` (run when the package is imported) finds the Python packages
`drivenbymoss` and `dbm_host`: on the Python path, else in `$DBM_PYTHON_DIR`, else in
`/usr/share/drivenbymoss/python` (the drivenbymoss package). The binding loads the native library
from `$DBM_LIBRARY`, which defaults to `/usr/lib/drivenbymoss/libdrivenbymoss.so` (the package).
libdbm_nihost (the Maschines in-process) is `$DBM_NIHOST_LIBRARY`, else
`/usr/lib/drivenbymoss/libdbm_nihost.so`.

- On a device: the drivenbymoss package; nothing to set.
- For development: a drivenbymoss-rust checkout, built with `cargo build --lib`:
  `DBM_PYTHON_DIR=<drivenbymoss-rust>/bindings/python` and
  `DBM_LIBRARY=<drivenbymoss-rust>/target/debug/libdrivenbymoss.so`.

Then `import_dbm` compares the binding's protocol (`drivenbymoss.protocol.VERSION_MAJOR` and
`HASH`) with the library's (`dbm_protocol_info`). On a different major version or table hash it
logs an error ("DrivenByMoss: the library … has protocol …: the dbm drivers are not loaded") once
and raises `DbmProtocolError` (an `ImportError`): zynthian's ctrldev manager then skips the dbm
driver modules and loads the others. Install a binding and a library of one build to fix it.

Controllers: the Novation Launch Control XL; the Native Instruments Maschine Mk2, which needs
dbm-nihost (`support/linux/ni_host`) for its MIDI ports, displays and Shift button; the Native
Instruments Maschine JAM, also through dbm-nihost (`Maschine Jam - 1 IN 1`); the Novation
Launchpad X, Mini MkIII, Pro Mk3, Pro and MkII on their MIDI ports. zynthian's own Launchpad
drivers (on the DAW ports) autoload; pick "DrivenByMoss Launchpad …" in the MIDI device options
of the MIDI port (`Launchpad X IN 2`), which then unloads zynthian's driver of that device
([plan §7b](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_PLAN.md)). The MkII has no zynthian driver and autoloads.

The core's browser browses the banks and presets of the active chain's current processor (the
Mk2's BROWSE: knob 1 the bank, knob 8 the preset, ENCODER PUSH loads, BROWSE again cancels);
meanwhile zynthian shows its preset view of that processor ([plan §3.7](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_PLAN.md)).
With zynthian's Preset Preload on, the preset under the cursor sounds, also after a bank change;
cancel brings back the bank and preset loaded before. The Mk2's knobs move one entry per knob
event (the core's browse mode), fast on knobs without detents; the encoder steps one per click.

On the Mk2 the group button of the "+" track (after the last chain) opens zynthian's Add Chain
view and the browse mode on its entries (the encoder moves, zynthian's grid follows; ENCODER PUSH
picks the chain type, BROWSE cancels); then the browse mode continues with zynthian's engine
screen (knob 1 the category, the encoder the engine; PUSH picks it, BROWSE goes back to the chain
types). zynthian then asks for the MIDI channel of a MIDI chain, or adds the chain at once
([plan §3.7b](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_PLAN.md)).

Knobs (relative changes) move stepped parameters (on/off switches, labels, integers) by whole
steps: a short turn switches a toggle (right on, left off) or moves one label
([plan §7](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_PLAN.md)).

The Maschine drivers drive the devices in zynthian's process with libdbm_nihost (the drivenbymoss
package, `/usr/lib/drivenbymoss/libdbm_nihost.so`, or `$DBM_NIHOST_LIBRARY`): zynthian's ctrldev
manager loads them without a MIDI port when the device is in `/sys/class/hidraw`
([doc/ZYNTHIAN_INTEGRATION.md §10](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/ZYNTHIAN_INTEGRATION.md)). dbm-nihost (the daemon)
must not run then. The same drivers still work on dbm-nihost's ports, as follows.

The Maschine drivers run their controller only while dbm-nihost reports the device (its hello,
and "gone" when it is unplugged): dbm-nihost creates the ports of both Maschines at its start, so
zynthian loads both drivers also without the devices. After a restart of dbm-nihost or a replug,
the controller starts again and sends all LEDs and displays. This needs a dbm-nihost of the
same drivenbymoss version; with an older one the JAM driver waits for a replug of the JAM.

The drivers read zynthian at two rates: the transport, the meters, the playing notes and steps on
every tick, the rest at once after a change signal of zynthian or a command of the controller,
else 4 times a second ([docs/dbm/ZYNTHIAN_CPU.md](../../../docs/dbm/ZYNTHIAN_CPU.md)). Send levels and processor parameters changed in
zynthian's UI therefore reach the controller within 250 ms.

The drivers use zynthian-ui's PipeWire port names, the `dev_in_2_dev_out` fix and
`getTransportState` in `zynseq.h` (all on this branch).

## The host's pages (chain control's grid)

With zynthian-ui's grid module (`zyngui/zynthian_control_grid_data.py` with `chain_pages` and
`shared_selection`: the `electra-grid` branch) a controller with a grid (the Maschine JAM:
Select + SONG) shows the active chain's controller pages as zynthian's grid layouts do, and its
selection is chain control's: a press on a cell selects its page and cell on zynthian's screen,
a change on the screen moves the controller's highlight (`dbm_zynthian/host_page.py`,
[doc/HOST_PAGE_PLAN.md §12](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/HOST_PAGE_PLAN.md)). Without that module (a stock zynthian)
the host-page commands are not declared and the controller has no host source.

## Device IDs from the environment

`ZYNTHIAN_DBM_DEVICE_<MODEL>` (the driver module's model, upper-cased, e.g.
`ZYNTHIAN_DBM_DEVICE_MASCHINE_JAM`; the JAM also reads `ZYNTHIAN_DBM_JAM_DEVICE`) replaces a
driver's device IDs: a comma-separated list of zynthian device IDs, e.g. `Maschine Jam - 1 (hp)
IN 1` for a simulator with a port suffix next to dbm-nihost's JAM. Read when the driver module is
loaded. The in-process HID matching (`hid_ids`) stays.

## Running zynthian against a DrivenByMoss checkout

```sh
cd <drivenbymoss-rust> && cargo build --lib
DBM_PYTHON_DIR=<drivenbymoss-rust>/bindings/python \
DBM_LIBRARY=<drivenbymoss-rust>/target/debug/libdrivenbymoss.so \
    <zynthian-ui>/desktop/zynthian_desktop.sh
```

## Tests

From zynthian-ui's root:

```sh
export DBM_PYTHON_DIR=<drivenbymoss-rust>/bindings/python
export DBM_LIBRARY=<drivenbymoss-rust>/target/debug/libdrivenbymoss.so
python3 tests/dbm/run_tests.py [-v]        # or ./run_tests.sh dbm [-v]
python3 tests/dbm/zyn_conformance.py launchcontrol_xl track_mix [phase|all]
python3 tests/dbm/zyn_conformance.py maschine_mk2 global 2
python3 tests/dbm/zyn_conformance.py maschine_jam session 3
```

Without `DBM_PYTHON_DIR` they use the installed drivenbymoss package; without either,
`run_tests.py` exits with 77 ("skipped"). They need plain Python 3.11+ (no JACK, no zynthian
dependencies: `tests/dbm/zynstubs.py` stands in for them, so pytest doesn't collect them:
`tests/dbm/conftest.py`). `$ZYNTHIAN_UI_DIR` runs them against another zynthian-ui checkout
(default: this one). The conformance tests also need the profiles of the Bitwig setups
(`~/.local/share/dbm-conformance/profiles/<setup>`, or `DBM_PROFILE_DIR`).
`tests/integration/test_ctrldev_drivers.py` (pytest) also runs the dbm drivers through its
contract when DrivenByMoss is found, and skips them otherwise.

The drivers talk to the core in the binary protocol only ([doc/TYPED_PROTOCOL_PLAN.md](https://github.com/hjanetzek/drivenbymoss-rust/blob/main/doc/TYPED_PROTOCOL_PLAN.md): one buffer
of records per report and per call, exact doubles), as `dbm_host`. The handled commands are
passed to the core, which derives the command features from them: the transport and the clip
launcher only with zynseq.

## Parameter values: polling, and zynthian's CC feedback broker

Checked 2026-11-21 against zynthian-ui on upstream tomita 3dbab929 (main 84de173ff).

- The driver reads parameter values itself on its tick thread (`dbm_zynthian/model.py`:
  `zctrl.value`, `zctrl.get_value2label()`), and the core compares them with what the device
  shows, as with Bitwig. That stays the model: no push notifications needed.
- Don't use `zctrl.is_dirty` for this: zynthian's UIs reset that flag when they redraw, so whoever
  reads it first consumes the change.
- zynthian no longer has per-controller value callbacks: upstream added a callback list
  (91d51107) and replaced it with the CC feedback broker (`zyngine/zynthian_cc_feedback.py`,
  d6d08865, 6f18babb). `zctrl.feedback` is the broker while the controller is bound to a
  registered device.
- The broker sends the values of MIDI-learned bindings (and bindings a driver sets with
  `set_bindings()`) back to devices that register their MIDI input with
  `register(zmip, cb, value)`; `cb(zctrl, chan, cc)` runs in whatever thread set the value. It
  doesn't fit DBM: it is keyed by MIDI input, so HID devices without a MIDI port (the Maschines)
  can't register, and DBM shows pages of parameters and the mixer rather than CC bindings.
- **Don't register a DBM-driven device with the broker.** It would send CC values to the device
  and compete with DBM's own LEDs and displays. The drivers don't register now.
- Possible later use: if a DBM-driven MIDI controller should also show a binding the user made by
  MIDI learn (an LED ring on a learned knob), registering with a `value` function that gives that
  device's representation is the built-in way to do it.
