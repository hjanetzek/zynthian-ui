#!/usr/bin/env python3
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

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QML_DIR = os.environ.get("PREVIEW_QML_DIR") or os.path.join(REPO, "zynqt", "qml")

COLORS = {"bg": "#000000", "tx": "#ffffff", "tx_off": "#e0e0e0", "on": "#ff0000", "off": "#5a626d",
          "hl": "#00c000", "ml": "#f0f000", "low_on": "#b00000", "panel_bg": "#3a424d",
          "panel_hl": "#2a323d", "info": "#8080ff", "midi": "#19b1f7", "alt": "#ff00ff",
          "alt2": "#ff9000", "error": "#ff0000", "warn": "#ff9000"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("out")
    ap.add_argument("-t", "--theme", default="classic")
    ap.add_argument("-s", "--size", default="800x480")
    a = ap.parse_args()
    w, h = (int(x) for x in a.size.split("x"))

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
        QTimer.singleShot(int(os.environ.get("PREVIEW_WAIT_MS", "700")), grab)
        app.exec()
    os.unlink(tmp.name)
    os.unlink(run_path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
