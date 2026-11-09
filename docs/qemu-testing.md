# Testing in a QEMU VM (for agents)

Test zynthian on Nura in a virtual machine on this desktop instead of in desktop mode on the
user's session, headless on the host, or on the Duet: the VM runs the same Nura image and
packages as the devices (kiosk session, PipeWire, the packaged engines and plugins), is isolated
from the user's desktop, can be reset at any time, and several can run side by side.

The image is nura-builds' amd64 build (`zynthian-qemu-amd64.img.zst` in its release
`zynthian-latest`, from Run workflow > architecture `x86_64` with images); the scripts are
nura-builds' `tools/run-qemu.sh` and `tools/qemu-setup.sh`, and this repository's `nura/tools`
with `-V`. Checked 2026-11-08 (headless VM, sync, session restart, screenshot).

## Rules

- **Your own VM**: its own cache directory (`-d`) and ports (`-p`, `-w`). The user's VM uses the
  defaults (`~/.cache/nura-builds`, SSH 2222, webconf 8080 or the next free port): never start,
  reset or log into that one.
- **Headless, no audio**: `-D none -A none`. A window or sound on the user's desktop disturbs them.
- **Stop it when done** (`kill $(cat DIR/qemu.pid)`); the disk stays for the next run.
- No USB passthrough (`-U`) without asking: the controllers belong to the user's sessions.
- Performance numbers (CPU per thread, latency) from the VM are not the Duet's: x86-64 with KVM
  against an ARM tablet. Measure on the Duet.

## Start a VM

```sh
cd ~/bastel/github/nura-builds
VM=$HOME/.cache/nura-builds-agent      # your directory
mkdir -p "$VM"
# first time: copy the user's downloaded image instead of downloading it again
[ -f "$VM/zynthian-qemu-amd64.img.zst" ] || cp ~/.cache/nura-builds/zynthian-qemu-amd64.img.zst "$VM/"
tools/run-qemu.sh -d "$VM" -D none -A silent -p 2232 -w 8092 < /dev/null > "$VM/run.log" 2>&1 &
```

(As a background command of your tool runner; it prints the ports, the serial log and how to stop it
to `run.log`.) The first boot of a fresh disk takes about a minute (it grows the root partition).

- `-r`: a fresh disk from the downloaded image (discards everything in the VM); `-u`: download a
  newer image (the user may have that one already: copy it from `~/.cache/nura-builds`).
- `-R WxH`: the screen, default 1280x800 (16:10 as the Duet; the kiosk uses scale 1 in a VM, so
  the layout is the Duet's). Other sizes for layout checks: `-R 1024x600`, `-R 800x480`.
- OpenGL: headless only with QEMU's `egl-headless` display (`qemu-ui-egl-headless` on Arch; ask the
  user to install it). Without it (`opengl: off` in run.log) the guest renders with llvmpipe: slower,
  fine for functional tests.
- Serial console: `$VM/serial.log`.
- `-A silent`: a sound card without host output (the audio clock runs, nothing is heard); `-A none`
  can stall PipeWire's graph in long tests (see Troubleshooting).

### Manual inspection: window and sound

To look at an agent's VM yourself, stop it and start the same disk with the defaults: a GTK
window (`-D gtk`) and virtio-sound through the desktop's PipeWire (`-A virtio`; `-A hda` for the
emulated Intel HDA card). Keep the ports, so agents can still reach it:

```sh
cd ~/bastel/github/nura-builds
ssh -p 2232 user@127.0.0.1 sudo poweroff        # or: kill $(cat ~/.cache/nura-builds-agent/qemu.pid)
tools/run-qemu.sh -d ~/.cache/nura-builds-agent -p 2232 -w 8092
# a VM started from a copied disk: the image path as last argument (see "A second VM")
tools/run-qemu.sh -d ~/.cache/nura-builds-agent-tk -p 2233 -w 8093 ~/.cache/nura-builds-agent-tk/zynthian-qemu-amd64.img
```

Turn the volume down: snapshots start playing when they load. Ctrl+Alt+G releases the mouse;
closing the window stops the VM.

## One-time setup per disk

```sh
tools/qemu-setup.sh -p 2232
```

Installs your SSH key for the VM's user and passwordless sudo (with the image's password once:
user `user`, password `147147`). Needed again after `-r`/`-u`. Then ssh works with BatchMode:

```sh
ssh -p 2232 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@127.0.0.1
```

(The host key changes with every fresh disk; don't record it in known_hosts.)

## Test your changes

This repository's `nura/tools` take `-V` for the VM (user@127.0.0.1, port `NURA_VM_PORT`, default
2222: set it to yours):

```sh
cd ~/bastel/github/zynthian-ui
export NURA_VM_PORT=2232
nura/tools/sync_ui.sh -V -r          # copy this checkout's Python code into the VM, restart the session
nura/tools/screenshot.sh -V out.png  # the kiosk screen (once: ssh ... sudo apk add grim)
nura/tools/zyninject.sh -V ...       # run code inside the running zynthian (see the script)
nura/tools/thread_cpu.sh -V          # CPU per thread (not the Duet's numbers)
nura/tools/switch_ui.sh -V tomita    # upstream zynthian-ui (Tk) instead of the Qt UI, and back: qt
```

- `sync_ui.sh` copies what `desktop/install.sh` installs as Python (zyngui, zyngine, zynconf,
  zynautoconnect, zynqt, the zynlibs modules, fonts, icons, img, the main scripts) into
  `/usr/share/zynthian/zynthian-ui`. Native code (zynlibs `.so`, zyncoder) isn't copied.
- Native changes: the package, built locally for x86_64 and installed:
  `nura/deploy.sh -a x86_64 -H 127.0.0.1 -P 2232 -u user -r zynthian-ui` (pmbootstrap builds missing
  x86_64 dependencies locally, which can take long; or let nura-builds CI build it and
  `sudo apk upgrade` in the VM, which has nura-builds' x86_64 repository).
- Other packages (drivenbymoss, zynthian-webconf, ...): `deploy.sh -a x86_64 -H 127.0.0.1 -P 2232
  -u user <package>`, or from the CI repository with `sudo apk add`/`upgrade`.
- zynthian's state and config in the VM: `~user/.config/zynthian`,
  `~user/.local/share/zynthian/my-data`; logs with `journalctl -b` in the VM.
- webconf: `http://localhost:8092` (your `-w` port), login user `user`, password `147147`.

## A second VM from the same disk (e.g. Tk and Qt side by side)

Stop the first VM cleanly (`sudo poweroff` in it), copy its disk to a directory of its own and
start the copy **with the image path as argument**: without it, `run-qemu.sh` finds no `.img.zst`
in that directory, downloads the latest image and unpacks it over the copy.

```sh
mkdir -p ~/.cache/nura-builds-agent-tk
cp --sparse=always ~/.cache/nura-builds-agent/zynthian-qemu-amd64.img ~/.cache/nura-builds-agent-tk/
tools/run-qemu.sh -d ~/.cache/nura-builds-agent-tk -D none -A silent -p 2233 -w 8093 \
    ~/.cache/nura-builds-agent-tk/zynthian-qemu-amd64.img
ssh -p 2233 user@127.0.0.1 'sudo sed -i "s/^ZYNTHIAN_UI=.*/ZYNTHIAN_UI=tk/" /etc/default/zynthian; sudo systemctl restart tinydm'
```

The tools take the port from `NURA_VM_PORT` with `-V` (`NURA_VM_PORT=2233 nura/tools/screenshot.sh -V out.png`).

## Stop

```sh
kill $(cat "$VM/qemu.pid")
```

## Troubleshooting

- `QEMU lacks modules ...`: the user has to install them (the message names the packages).
- `can't download the image`: GitHub's release downloads fail at times (HTTP 503/504; the script
  retries through the API); copy the user's image from `~/.cache/nura-builds` instead.
- No SSH after a minute: `tail $VM/serial.log` (a login prompt there means the system is up).
- zynthian hangs removing chains (a snapshot load that never finishes; a thread dump shows
  `zynmixer.remove_strip` → `removeStrip`): the VM has no sound card with `-A none`, and its PipeWire
  graph can stop (pw-top: every node at quantum 0, zynthian's nodes driven by `Midi-Bridge`). zynmixer
  waits for a JACK period that never comes (upstream log: `removeStrip()`). Restart the session
  (`sudo systemctl restart tinydm`); for long runs use `-A silent` (an Intel HDA card on QEMU's
  `none` backend: the guest's audio clock runs, nothing reaches the host). Seen 2026-11-08, cause
  of the stop not known yet.
- SSH times out "during banner exchange" after a reboot of the VM: the guest got 10.0.2.16, the
  port forward goes to 10.0.2.15. Before 2026-11-09 the firmware tried PXE on the virtio NIC before
  the disk, with the NIC's own MAC, and took .15 from QEMU's DHCP; NetworkManager (cloned "stable"
  MAC) then got .16 and asks for it again at every boot. `run-qemu.sh` now boots the disk first
  (`bootindex=0`, no NIC ROM, OVMF's PXE off). A disk that has the .16 lease: start it fresh (`-r`),
  or delete `/var/lib/NetworkManager/internal-*-eth0.lease` in the guest. Not with `debugfs -w` on
  a VM that was killed: the ext4 journal replay at the next boot brings the file back.
