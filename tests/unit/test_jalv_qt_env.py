"""zyngine.zynthian_engine_jalv.set_plugin_qt_platform: jalv processes don't inherit zynthian's
own Qt platform (eglfs/linuxfb/wayland), Qt plugin UIs (synthv1 & co.) create a QApplication."""

import sys

import zyngine.zynthian_engine_jalv  # noqa: F401 (the module: zyngine/__init__ star-imports the classes)


def session_env():
    # As zynthian's session on a Galaxy S III Neo (eglfs) with a scaled UI
    return {
        "PATH": "/usr/bin", "HOME": "/home/user", "DISPLAY": ":0", "QT_PLUGIN_PATH": "/usr/lib/qt6/plugins",
        "QT_QPA_PLATFORM": "eglfs", "QT_QPA_EGLFS_INTEGRATION": "eglfs_kms",
        "QT_QPA_EGLFS_KMS_CONFIG": "/etc/kms.json", "QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS": "/dev/input/event1",
        "QT_QPA_FB_HIDECURSOR": "1", "QT_SCALE_FACTOR": "1.5", "QT_SCALE_FACTOR_ROUNDING_POLICY": "PassThrough",
    }


def set_platform(env, platform):
    sys.modules["zyngine.zynthian_engine_jalv"].set_plugin_qt_platform(env, platform)


def test_console_jalv_gets_offscreen_and_none_of_the_sessions_qt_platform_settings():
    env = session_env()
    set_platform(env, "offscreen")
    assert env["QT_QPA_PLATFORM"] == "offscreen"
    assert not [n for n in env if n.startswith(("QT_QPA_", "QT_SCALE_")) and n != "QT_QPA_PLATFORM"]
    # the rest stays
    assert env["PATH"] == "/usr/bin" and env["DISPLAY"] == ":0"
    assert env["QT_PLUGIN_PATH"] == "/usr/lib/qt6/plugins"


def test_jalv_gtk_with_a_native_gui_gets_xcb():
    env = dict(session_env(), QT_QPA_PLATFORM="wayland", GDK_BACKEND="x11")
    set_platform(env, "xcb")
    assert env["QT_QPA_PLATFORM"] == "xcb"
    assert "QT_SCALE_FACTOR" not in env and "QT_QPA_EGLFS_INTEGRATION" not in env
    assert env["GDK_BACKEND"] == "x11"


def test_without_session_settings():
    env = {"PATH": "/usr/bin"}
    set_platform(env, "offscreen")
    assert env == {"PATH": "/usr/bin", "QT_QPA_PLATFORM": "offscreen"}
