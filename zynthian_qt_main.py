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
import os
import signal
import sys

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

# zynthian's settings; Tk is only set up there for zynthian_main.py
from zyngui import zynthian_gui_config
# Before the engine modules are imported: zynthian_chain_manager queries zyncore at import
zynthian_gui_config.init_zyncore()

from zynqt.keyboard import KeyBindingFilter, load_bindings
from zynqt.ui import ZynUI
from zynqt.models.mixer import MixerModel, MixerMeters
from zynqt.models.organelle import OledDisplay

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


def main():
    logging.info("STARTING ZYNTHIAN-UI (Qt) ...")
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
    engine.load(QUrl.fromLocalFile(os.path.join(QML_DIR, "Main.qml")))
    if engine.rootObjects():
        key_filter = KeyBindingFilter(ui, engine.rootObjects()[0])
        engine.rootObjects()[0].installEventFilter(key_filter)
    if not engine.rootObjects():
        logging.error("Can't load the QML UI")
        return 1

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
    return ui.exit_code


if __name__ == "__main__":
    sys.exit(main())
