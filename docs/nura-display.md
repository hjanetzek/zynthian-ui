# Display stack on the Lenovo Duet: findings

Status: 2026-11-04. Device: Lenovo IdeaPad Duet (MT8183, Mali-G72 MC3 with Panfrost, DSI panel
1200×1920 in portrait, used rotated to 1920×1200). Software: postmarketOS kernel 7.2.7-mt81,
Mesa 26.2.5, Xwayland 24.1.14, Xorg modesetting driver, Tk 8.6.17.

## Result

Use **cage (wlroots) with XWayland started with `-glamor off`**. It is the only setup tested here
that draws correctly, and the rotation and frame presentation stay on the GPU (in the compositor).

| Setup | Result |
|---|---|
| cage + XWayland, glamor (GLES, the default) | black rectangles in Tk widgets |
| cage + XWayland, `-glamor gl` (desktop GL) | same black rectangles |
| cage + XWayland, `-glamor off` | correct |
| Xorg modesetting, glamor | partial updates, regions not redrawn |
| Xorg modesetting, `AccelMethod none` | correct, but rotation in software: repaints visibly (like e-paper) |
| Xorg in general | the device hangs when the display pipe is switched off (see below) |

## glamor on Panfrost leaves regions undrawn

Symptom: small black rectangles in the empty part of a Tk listbox (bottom right), which change
with every redraw of the list (selecting an item, clicking the empty list area) and stay when
nothing redraws it (side buttons).

- They are in the X window's own content: `xwd -id <tk window>` shows them as well as grim does,
  so it is not damage lost by the compositor.
- No widget is there (`winfo_containing`), the listbox geometry doesn't change.
- Tk's listbox (tkListbox.c, `DisplayListbox`) redraws the whole widget on every redraw: it fills
  a new pixmap with the background, draws the items and copies the pixmap to the window. A forced
  redraw (`listbox.configure(bg=...)`) clears the rectangles.
- Black is the content of a newly allocated pixmap: parts of the fill or the copy are lost.
- With XWayland `-glamor off` the rectangles are gone; with `-glamor gl` they come back, so the
  bug is in glamor on Panfrost, not in its GLES path. Xorg with glamor shows the same as partial
  updates on some screens.

Likely a Mesa (Panfrost) or glamor bug; a Tk listbox redrawn on this device reproduces it reliably.

## Xorg hangs mediatek-drm when the display pipe is switched off

Starting Xorg and then calling `xset -dpms` / `xrandr --rotate` hung the whole device about two
seconds after start (no ssh, no ping):

```
mediatek-drm mediatek-drm.17.auto: [drm] vblank wait timed out on crtc 0
WARNING: drivers/gpu/drm/drm_vblank.c:1329 at drm_crtc_wait_one_vblank (Xorg)
  drm_atomic_helper_commit_crtc_disable
  drm_atomic_connector_commit_dpms
  drm_connector_property_set_ioctl
cros-ec-spi spi2.0: SPI transfer timed out     (repeated until the device hung)
```

Switching the connector's DPMS state disables the active CRTC, the vblank wait never ends, and
afterwards the kernel can't reach the embedded controller over SPI. Cage enables the panel once
and never switches it off, so it isn't affected. With rotation, blanking and DPMS configured in
`xorg.conf` (applied in the first modeset) and no display changes afterwards, Xorg ran.

## Setup on the device

XWayland without glamor: wlroots starts the binary named in `WLR_XWAYLAND`. The variable has to
be set before cage starts, i.e. in tinydm's session environment, not in `/etc/cage-ui/*.sh`
(those are sourced by the session script, which cage runs after it has started XWayland).

`/usr/local/bin/xwayland-noglamor`:

```sh
#!/bin/sh
exec /usr/bin/Xwayland "$@" -glamor off
```

`/etc/tinydm.d/env-wayland.d/90-xwayland-noglamor.sh`:

```sh
export WLR_XWAYLAND=/usr/local/bin/xwayland-noglamor
```

Check: `ps -o args= -C Xwayland` ends with `-glamor off`.

The X11 experiment (`/usr/share/xsessions/zynthian-x11.desktop`,
`/usr/local/bin/zynthian-x11-session`, `/etc/X11/xorg.conf.d/20-zynthian-kms.conf`) is installed
on the device but not the default session. To try it once without making it the default (a
reboot returns to cage):

```sh
sudo ln -sf /usr/share/xsessions/zynthian-x11.desktop /var/lib/tinydm/default-session.desktop
sudo systemctl restart tinydm; sleep 3
sudo ln -sf /usr/share/wayland-sessions/cage-ui.desktop /var/lib/tinydm/default-session.desktop
```

## Open

- Measure the cost of XWayland without glamor (screen switch times with
  `nura/tools/screen_timing.py`, XWayland CPU while the mixer meters run); before: 25–36 ms per
  screen switch with glamor.
- Add the XWayland wrapper and session environment to the `postmarketos-ui-zynthian` package.
- Report the glamor/Panfrost bug to Mesa, and the vblank timeout to the mediatek-drm maintainers.
- Under X11, zynthian didn't exit on SIGTERM (main thread waiting on a lock); not looked at.
