"""zyngui.zynthian_audio_file_data.file_zctrl: the path controller the audio file view shows
(Tk widget and Qt view). Upstream's #1847 fix (5b0b6966), ported into the shared module: on a page
without a file controller it takes a path controller for audio files, not just the first one
(samplv1 also has tuning scale and keymap files)."""

from types import SimpleNamespace

from zyngui import zynthian_audio_file_data as afd


def path(symbol, types=None):
    return SimpleNamespace(symbol=symbol, is_path=True, path_file_types=types)


def proc(*zctrls):
    # No selected phrase: not clippy, so no "file N" controller
    return SimpleNamespace(engine=SimpleNamespace(), controllers_dict={z.symbol: z for z in zctrls})


def test_prefers_the_path_controller_for_audio_files():
    sample = path("sample", ["wav", "flac"])
    p = proc(path("tuning", ["scl"]), path("keymap", ["kbm"]), sample)
    assert afd.file_zctrl(p) is sample


def test_falls_back_to_a_path_controller_without_file_types():
    untyped = path("file")
    p = proc(path("tuning", ["scl"]), untyped, path("other"))
    assert afd.file_zctrl(p) is untyped


def test_none_without_an_audio_path_controller():
    assert afd.file_zctrl(proc(path("tuning", ["scl"]), SimpleNamespace(symbol="x", is_path=False))) is None


def test_the_widget_controller_and_the_clip_controller_come_first():
    widget = path("w")
    assert afd.file_zctrl(proc(path("sample", ["wav"])), widget) is widget
    clip = path("file 2")
    p = SimpleNamespace(engine=SimpleNamespace(selected_phrase=1), controllers_dict={"file 2": clip})
    assert afd.file_zctrl(p) is clip
