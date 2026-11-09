#!/usr/bin/python3
"""Render a QML scene of the Qt UI offscreen to a PNG, for iterating on themes without a device:

    QT_QPA_PLATFORM=offscreen python3 nura/tools/qml_preview.py SCENE.qml OUT.png [-t THEME] [-s WxH]

SCENE.qml is a QML file whose root is an Item; it can `import "<repo>/zynqt/qml"` (the path is in
the import path as "ZynQml": `import ZynQml` does not work for a plain directory, so scenes use the
absolute path, which this tool substitutes for @QML@). The theme is a file selector as in
zynthian_qt_main.py, the fonts are the repository's fonts/ (as on the device), and zynConfig holds
the Tk sizing values (ZYNTHIAN_UI_SCALE=auto, font size 16, the default colours) unless the
environment says otherwise. Mock data (screens, models) belong in the scene."""

import argparse
import os
import sys
import tempfile

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QML_DIR = os.environ.get("PREVIEW_QML_DIR") or os.path.join(REPO, "zynqt", "qml")

COLORS = {"bg": "#000000", "tx": "#ffffff", "tx_off": "#e0e0e0", "on": "#ff0000", "off": "#5a626d",
          "hl": "#00c000", "ml": "#f0f000", "low_on": "#b00000", "panel_bg": "#3a424d",
          "panel_hl": "#2a323d", "info": "#8080ff", "midi": "#19b1f7", "alt": "#ff00ff",
          "alt2": "#ff9000", "error": "#ff0000", "warn": "#ff9000"}


class MockStrips(QAbstractListModel):
    """Mixer strips as zynqt.models.mixer.MixerModel's roles (--mixer)"""
    ROLES = ["chainId", "name", "midiChan", "level", "balance", "mute", "solo", "record", "isMixbus",
             "meterIndex", "active", "toggle", "toggleLabel", "description", "legend", "hasMixer", "activeMidi"]
    countChanged = Signal()

    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def roleNames(self):
        return {Qt.UserRole + 1 + i: r.encode() for i, r in enumerate(self.ROLES)}

    def data(self, index, role):
        return self.rows[index.row()].get(self.ROLES[role - Qt.UserRole - 1])

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.rows)

    @Slot(int, float)
    def setLevel(self, r, v): pass

    @Slot(int, float)
    def setBalance(self, r, v): pass

    @Slot(int)
    def toggleMute(self, r): pass

    @Slot(int)
    def toggleControl(self, r): pass


class MockMeters(QObject):
    levelsChanged = Signal()
    activeChanged = Signal()

    def __init__(self, levels):
        super().__init__()
        self._levels = levels
        self._active = False

    @Property("QVariantList", notify=levelsChanged)
    def levels(self):
        return self._levels

    def _ga(self):
        return self._active

    def _sa(self, v):
        self._active = v
    active = Property(bool, _ga, _sa, notify=activeChanged)


class MockZyn(QObject):
    changed = Signal()

    def __init__(self, screen="mixer"):
        super().__init__()
        self._screen = screen

    @Property(str, notify=changed)
    def currentScreen(self):
        return self._screen

    @Property(int, notify=changed)
    def visibleChains(self):
        return 0

    @Property(bool, notify=changed)
    def altMode(self):
        return False

    @Property("QVariantMap", notify=changed)
    def status(self):
        return {}

    @Slot(int, bool)
    def pushSwitch(self, i, p): pass

    @Slot(int)
    def selectChain(self, c): pass

    @Slot(int)
    def openChain(self, c): pass

    @Slot(int)
    def openChainManagerOptions(self, c): pass


def strip(cid, desc, legend, level, active=False, midi=0, mixbus=False, mute=False, toggle=False):
    return {"chainId": cid, "name": desc.split("\n")[0], "midiChan": midi, "level": level, "balance": 0.0,
            "mute": mute, "solo": False, "record": toggle, "isMixbus": mixbus, "meterIndex": 0,
            "active": active, "toggle": toggle, "toggleLabel": "R", "description": desc,
            "legend": legend, "hasMixer": True, "activeMidi": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("out", nargs="?", default="", help="PNG to write (not with --live)")
    ap.add_argument("--live", action="store_true",
                    help="show the scene in a window and keep running, with QML debugging for Qt 6's "
                         "qmlpreview (hot reload of zynqt/qml): /usr/lib/qt6/bin/qmlpreview "
                         "./nura/tools/qml_preview.py SCENE.qml --live")
    ap.add_argument("-t", "--theme", default="classic")
    ap.add_argument("-s", "--size", default="800x480")
    ap.add_argument("--mixer", action="store_true", help="mock mixer strips (the compare snapshot)")
    # qmlpreview adds -qmljsdebugger=... (Qt reads it from sys.argv)
    a, _ = ap.parse_known_args()
    w, h = (int(x) for x in a.size.split("x"))

    if a.live:
        from PySide6.QtQml import QQmlDebuggingEnabler
        QQmlDebuggingEnabler.enableDebugging(True)
    else:
        if not a.out:
            ap.error("OUT is needed without --live")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication(sys.argv)
    for root, _, files in os.walk(os.path.join(REPO, "fonts")):
        for f in files:
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(root, f))

    src = open(a.scene).read().replace("\"@QML@\"", "\"file:" + QML_DIR + "\"").replace("@QML@", QML_DIR)
    wrapper = f"""import QtQuick
import QtQuick.Window
import "file:{QML_DIR}"
Window {{
    width: {w}; height: {h}; visible: true; color: Theme.background
    Binding {{ target: Theme; property: "screenWidth"; value: {w} }}
    Binding {{ target: Theme; property: "screenHeight"; value: {h} }}
    Loader {{ anchors.fill: parent; source: "{os.path.abspath(a.scene)}.run.qml" }}
}}
"""
    run_path = os.path.abspath(a.scene) + ".run.qml"
    open(run_path, "w").write(src)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".qml", delete=False, dir=os.path.dirname(run_path))
    tmp.write(wrapper)
    tmp.close()

    engine = QQmlApplicationEngine()
    if a.theme != "classic":
        engine.setExtraFileSelectors([a.theme])
    ctx = engine.rootContext()
    ctx.setContextProperty("zynThemeName", a.theme)
    ctx.setContextProperty("zynConfig", {
        "fontSize": int(os.environ.get("ZYNTHIAN_UI_FONT_SIZE", "16")),
        "uiScale": os.environ.get("ZYNTHIAN_UI_SCALE", "auto"),
        "mainMenuColumns": 0, "v5": False, "colors": COLORS})
    if a.mixer:
        rows = [strip(1, "ZynAddSubFX\nMetal Drips", "\u266b 1", 0.383),
                strip(2, "ZynAddSubFX\nVangelis Saw - C", "\u266b 1", 0.459, active=True),
                strip(3, "Audio Input 1,2\nCalf Phaser", "\uf130", 0.57)]
        for i, r in enumerate(rows):
            r["meterIndex"] = i
        mocks = [MockStrips(rows), MockStrips([strip(0, "Main\nSC4", "Main", 0.8)]),
                 MockMeters([0.0] * 12), MockMeters([0.0] * 4), MockZyn()]
        app._mocks = mocks
        for m in mocks:
            m.setParent(app)
        for name, m in zip(("mixerStrips", "mainStrip", "mixerMeters", "mainMeters", "zyn"), mocks):
            ctx.setContextProperty(name, m)
    engine.warnings.connect(lambda ws: [print("QML:", x.toString(), file=sys.stderr) for x in ws])
    engine.load(QUrl.fromLocalFile(tmp.name))
    roots = engine.rootObjects()
    rc = 0
    if not roots:
        print("scene did not load", file=sys.stderr)
        rc = 1
    else:
        win = roots[0]

        def grab():
            img = win.grabWindow()
            img.save(a.out)
            app.quit()
        if not a.live:
            QTimer.singleShot(int(os.environ.get("PREVIEW_WAIT_MS", "700")), grab)
        app.exec()
    os.unlink(tmp.name)
    os.unlink(run_path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
