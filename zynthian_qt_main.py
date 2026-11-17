#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Main Script for the Qt Quick UI (docs/qt-port-plan.md), started instead of zynthian_main.py
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import logging
import glob
import os
import signal
import sys


def run_under_qmlpreview():
    """ZYNTHIAN_QT_QMLPREVIEW=1 (development only, docs/qt-theming.md): run this script again as a
    child of Qt 6's qmlpreview, which reloads changed QML files in the running UI. qmlpreview
    passes -qmljsdebugger=... to the child, and always exits with 0 itself: the child writes its
    exit code to a file, which this process returns to the launcher (100/102 restart, 0 power
    off). Before the zynthian imports: this process sets up nothing."""
    qmlpreview = "/usr/lib/qt6/bin/qmlpreview"  # Qt 6's (a Qt 5 one silently does nothing)
    if (os.environ.get("ZYNTHIAN_QT_QMLPREVIEW") != "1" or os.environ.get("ZYNTHIAN_QT_EXIT_FILE")
            or not os.access(qmlpreview, os.X_OK)):
        return
    import subprocess
    import tempfile
    fd, exit_file = tempfile.mkstemp(prefix="zynthian-exit-")
    os.close(fd)
    env = dict(os.environ, ZYNTHIAN_QT_EXIT_FILE=exit_file)
    # The script itself (executable, #!/usr/bin/python3): qmlpreview appends its option after
    # the program, "python3 script" would get it as the interpreter's
    proc = subprocess.Popen([qmlpreview, "--verbose", os.path.abspath(__file__)] + sys.argv[1:], env=env)
    for signo in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signo, lambda s, f: proc.send_signal(s))
    while True:
        try:
            proc.wait()
            break
        except InterruptedError:
            pass
    try:
        code = int(open(exit_file).read().strip())
    except (OSError, ValueError):
        code = 2  # the child crashed: restart (not 1, that drops the last state)
    os.unlink(exit_file)
    sys.exit(code)


def report_exit(code):
    """The exit code for run_under_qmlpreview()"""
    exit_file = os.environ.get("ZYNTHIAN_QT_EXIT_FILE")
    if exit_file:
        with open(exit_file, "w") as f:
            f.write(str(code))
    return code


run_under_qmlpreview()

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

# zynthian's settings; Tk is only set up there for zynthian_main.py
from zyngui import zynthian_gui_config
# Tk's sizing settings as the launcher gave them (zynthian_custom_config.sh included), read now as
# Tk does at its start: the state manager's load_config() later sets the environment again from
# zynthian_envars.sh alone
TK_SIZING = {
    "fontSize": zynthian_gui_config.get_env_int("ZYNTHIAN_UI_FONT_SIZE", 16),
    "uiScale": os.environ.get("ZYNTHIAN_UI_SCALE", "").strip(),
    "mainMenuColumns": zynthian_gui_config.get_env_int("ZYNTHIAN_UI_MAIN_MENU_COLUMNS", 0),
}
# Before the engine modules are imported: zynthian_chain_manager queries zyncore at import
zynthian_gui_config.init_zyncore()

from zynqt.keyboard import KeyBindingFilter, load_bindings
from zynqt.ui import UserActivityFilter, ZynUI
from zynqt.models.mixer import MixerModel, MixerMeters
from zynqt.models.organelle import OledDisplay
from zynqt import theme as zyntheme

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zynqt", "qml")

# Exit codes as zynthian_main.py (the launchers restart on 100 and 102)
EXIT_CODES = {signal.SIGHUP: 0, signal.SIGINT: 100, signal.SIGQUIT: 102, signal.SIGTERM: 101}


def add_switch_timing(ui, window):
    """ZYNTHIAN_QT_TIMING=1: log the time from each screen switch to the next frame on screen
    (from the start of ZynUI._set_current_screen to QQuickWindow.frameSwapped, which the render
    thread emits)"""
    import time
    pending = {}

    def switched():
        # From the start of the switch (ZynUI._set_current_screen), list building included
        pending["t0"] = getattr(ui, "switch_t0", None) or time.monotonic()
        pending["screen"] = ui.current_screen

    def swapped():
        t0 = pending.pop("t0", None)
        if t0 is not None:
            logging.warning(f"SCREEN TIMING {pending.get('screen')}: {1000 * (time.monotonic() - t0):.1f} ms to frame"
                            f" (build {getattr(ui, 'switch_build_ms', 0):.1f} ms)")

    ui.currentScreenChanged.connect(switched)
    window.frameSwapped.connect(swapped, Qt.DirectConnection)


def mark_first_frame(window):
    """Write a marker file when the first frame is on screen (QQuickWindow.frameSwapped): a boot
    splash can stay until zynthian is visible (Nura's zynthian kits end Plymouth on it,
    device-zynthian-rpi4). ZYNTHIAN_FIRST_FRAME_FILE, default $XDG_RUNTIME_DIR/zynthian-first-frame
    (or /tmp). Then, once Plymouth is gone, the whole window is drawn once more: on a framebuffer
    (Qt linuxfb) only changed areas are drawn, and the splash drew on until it was ended, so its last
    frame stayed where zynthian hadn't changed anything yet."""
    path = os.environ.get("ZYNTHIAN_FIRST_FRAME_FILE") or os.path.join(
        os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "zynthian-first-frame")
    try:
        os.remove(path)
    except OSError:
        pass
    done = []

    def splash_running():
        """plymouthd running (by its process name: its pid file isn't always there at boot)"""
        for comm in glob.glob("/proc/[0-9]*/comm"):
            try:
                if open(comm).read().strip() == "plymouthd":
                    return True
            except OSError:
                pass
        return False

    # Polled in the GUI thread (frameSwapped comes in the render thread and only sets a flag):
    # after the first frame, once the splash is gone, the whole window once more
    timer = QTimer(window)
    timer.setInterval(200)
    polls = []

    def repaint_after_splash():
        polls.append(1)
        if len(polls) > 900:   # 3 minutes
            timer.stop()
            return
        if not done or splash_running():
            return
        timer.stop()
        # The whole window dirty: the content's opacity changed and back (every item repainted;
        # the window colour alone isn't enough, the content covers the background)
        item = window.contentItem()
        opacity = item.opacity()
        item.setOpacity(opacity * 0.99)
        QTimer.singleShot(100, lambda: item.setOpacity(opacity))
        logging.info("boot splash gone: the whole window drawn again")

    timer.timeout.connect(repaint_after_splash)
    if splash_running():
        timer.start()

    def swapped():
        if done:
            return
        done.append(True)
        try:
            open(path, "w").close()
        except OSError as e:
            logging.warning(f"first frame marker {path}: {e}")

    window.frameSwapped.connect(swapped, Qt.DirectConnection)


def preview_qml_dir():
    """Under qmlpreview: the QML directory through a symlink outside /usr. The QML preview service
    never asks qmlpreview for files under Qt's own prefix (QLibraryInfo::PrefixPath, /usr with the
    system's Qt): the files from /usr/share/zynthian were loaded as usual, qmlpreview watched
    nothing and reloaded nothing. The symlink's path isn't checked further. A link to the whole
    zynthian-ui directory: the QML refers to ../../icons etc."""
    if not os.environ.get("ZYNTHIAN_QT_EXIT_FILE"):
        return None
    link = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "zynthian-ui")
    try:
        if os.path.islink(link):
            os.unlink(link)
        os.symlink(os.path.dirname(os.path.dirname(QML_DIR)), link)
    except OSError as e:
        logging.warning(f"QML preview: no symlink {link} ({e}), no hot reload")
        return None
    return os.path.join(link, "zynqt", "qml")


def main():
    logging.info("STARTING ZYNTHIAN-UI (Qt) ...")
    # QML hot reload for development: under qmlpreview (run_under_qmlpreview), which passes
    # -qmljsdebugger=... (Qt reads it from sys.argv). Never without the variable: the debug server
    # is a remote control.
    if os.environ.get("ZYNTHIAN_QT_EXIT_FILE"):
        from PySide6.QtQml import QQmlDebuggingEnabler
        QQmlDebuggingEnabler.enableDebugging(True)
        logging.warning("QML debugging enabled (ZYNTHIAN_QT_QMLPREVIEW=1)")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("zynthian")
    # The Wayland app_id: compositors match windows by it (zynthian-niri's window rules)
    app.setDesktopFileName("zynthian")
    app.setOrganizationName("zynthian")
    # Icon font of the status bar (as the Tk UI), shipped with zynthian-ui
    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "fonts/ForkAwesome/forkawesome-webfont.ttf"))

    ui = ZynUI()
    zynthian_gui_config.zyngui = ui
    # Computer keyboard bindings (webconf: UI > Keyboard Binding): read now, the filter goes on
    # the window below (an application-wide filter would also be called for events of objects in
    # Qt's other threads, e.g. the render thread: crashes)
    load_bindings()

    mixer = MixerModel(ui.chain_manager, ui.bridge)
    main_bus = MixerModel(ui.chain_manager, ui.bridge, main_only=True)
    meters = MixerMeters(ui.state_manager, mixer)
    main_meters = MixerMeters(ui.state_manager, main_bus)
    ui.mixerSettingsChanged.connect(mixer.reload)
    ui.mixerSettingsChanged.connect(main_bus.reload)

    # QML types implemented in Python
    qmlRegisterType(OledDisplay, "Zynthian", 1, 0, "OledDisplay")
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("zyn", ui)
    ctx.setContextProperty("mixerStrips", mixer)
    ctx.setContextProperty("mainStrip", main_bus)
    ctx.setContextProperty("mixerMeters", meters)
    ctx.setContextProperty("mainMeters", main_meters)
    ctx.setContextProperty("startFullScreen", os.environ.get("ZYNTHIAN_FULLSCREEN") == "1")
    # Rotation of the whole UI in QML (Main.qml), for displays nobody rotates (eglfs on KMS)
    try:
        ui_rotation = int(os.environ.get("ZYNTHIAN_UI_ROTATION", "0") or 0) % 360
    except ValueError:
        ui_rotation = 0
    ctx.setContextProperty("zynUiRotation", ui_rotation if ui_rotation in (0, 90, 180, 270) else 0)
    # UI theme: file selectors, so zynqt/qml/+<theme>/X.qml replaces X.qml (its Theme.qml, the
    # components it draws differently); tk is zynqt/qml/ itself (zynqt/theme.py)
    theme, theme_selectors = zyntheme.theme_selectors(os.environ.get("ZYNTHIAN_QT_THEME"), QML_DIR)
    # What the Tk UI sizes and colours itself by (zynthian_gui_config), for themes that follow it
    # (tk): the font size before scaling, the scale ("auto": screen height / 600), the colours
    cfg = zynthian_gui_config
    ctx.setContextProperty("zynConfig", {
        **TK_SIZING,
        "v5": bool(cfg.check_wiring_layout(("V5", "Z2"))),
        # The touch keypad on the right (ZYNTHIAN_UI_TOUCH_NAVIGATION v5_keypad_right)
        "keypadRight": cfg.touch_navigation == "v5_keypad_right",
        "colors": {k[6:]: getattr(cfg, k) for k in dir(cfg) if k.startswith("color_") and isinstance(getattr(cfg, k), str)},
    })
    ctx.setContextProperty("zynThemeName", theme)
    if theme_selectors:
        engine.setExtraFileSelectors(theme_selectors)
    engine.load(QUrl.fromLocalFile(os.path.join(preview_qml_dir() or QML_DIR, "Main.qml")))
    if engine.rootObjects():
        mark_first_frame(engine.rootObjects()[0])
        key_filter = KeyBindingFilter(ui, engine.rootObjects()[0])
        engine.rootObjects()[0].installEventFilter(key_filter)
        # Installed last, so it sees the keys first: user activity for power save
        activity_filter = UserActivityFilter(ui, engine.rootObjects()[0])
        engine.rootObjects()[0].installEventFilter(activity_filter)
    if not engine.rootObjects():
        # A QML error (the messages above). Leave at once: returning ran the interpreter's
        # shutdown with the JACK clients (zynmixer, engines) still calling into Python from
        # PipeWire's data thread, which segfaulted (core dumps filled the disk in a restart
        # loop). Not status 1: the launcher would drop the last state, which isn't the cause.
        logging.error("Can't load the QML UI")
        logging.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(report_exit(2))

    if os.environ.get("ZYNTHIAN_QT_TIMING") == "1":
        add_switch_timing(ui, engine.rootObjects()[0])

    # Python runs its signal handlers only between bytecodes; let it run now and then while Qt's
    # event loop is in C++
    tick = QTimer(interval=200)
    tick.timeout.connect(lambda: None)
    tick.start()
    for signo, code in EXIT_CODES.items():
        signal.signal(signo, lambda s, f, code=code: ui.exit(code))

    ui.start()
    app.exec()
    logging.info(f"EXITING ZYNTHIAN-UI (Qt) => {ui.exit_code}")
    return report_exit(ui.exit_code)


if __name__ == "__main__":
    sys.exit(main())
