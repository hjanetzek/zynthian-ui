"""SS_ZS3_LIST: the real state manager sends it whenever the ZS3 list changes.

Save (new and update), delete, rename, note, clone, move, id change (a program change binding),
reset, and a snapshot load that replaces all ZS3s.
"""

import pytest

from zyngine.zynthian_signal_manager import zynsigman


@pytest.fixture
def zs3_signals(state_manager):
    sent = []

    def cb(**kwargs):
        sent.append(kwargs)

    zynsigman.register(zynsigman.S_STATE_MAN, zynsigman.SS_ZS3_LIST, cb)
    yield sent
    zynsigman.unregister(zynsigman.S_STATE_MAN, zynsigman.SS_ZS3_LIST, cb)


def test_save_new_and_update_send_it(state_manager, zs3_signals):
    state_manager.save_zs3("*/3")
    assert len(zs3_signals) == 1
    state_manager.save_zs3("*/3")
    assert len(zs3_signals) == 2
    assert "*/3" in state_manager.get_zs3_ids()


def test_delete_sends_it_and_a_missing_id_does_not(state_manager, zs3_signals):
    state_manager.save_zs3("*/3")
    zs3_signals.clear()
    state_manager.delete_zs3("*/3")
    assert len(zs3_signals) == 1
    state_manager.delete_zs3("*/3")
    assert len(zs3_signals) == 1


def test_title_note_clone_move(state_manager, zs3_signals):
    state_manager.save_zs3("zs3-0")  # the default state, as a snapshot has it
    state_manager.save_zs3()
    state_manager.save_zs3()
    first, second = state_manager.get_zs3_ids()
    zs3_signals.clear()
    state_manager.set_zs3_title(first, "Verse")
    state_manager.set_zs3_note(first, "a note")
    assert len(zs3_signals) == 2
    clone = state_manager.clone_zs3(first)
    assert len(zs3_signals) == 3  # one, although the clone is also moved in place
    assert state_manager.get_zs3_ids() == [first, clone, second]
    assert state_manager.move_zs3(second, 0)
    assert len(zs3_signals) == 4
    assert not state_manager.move_zs3(second, 0)  # no change, no signal
    assert len(zs3_signals) == 4


def test_change_zs3_id_keeps_the_place_and_the_active_zs3(state_manager, zs3_signals):
    state_manager.save_zs3("zs3-1")
    state_manager.save_zs3("zs3-2")
    state_manager.save_zs3("zs3-3")
    state_manager.last_zs3_id = "zs3-2"
    zs3_signals.clear()
    assert state_manager.change_zs3_id("zs3-2", "*/7")
    assert state_manager.get_zs3_ids() == ["zs3-1", "*/7", "zs3-3"]
    assert state_manager.last_zs3_id == "*/7"
    assert len(zs3_signals) == 1
    assert not state_manager.change_zs3_id("zs3-0", "*/8")
    assert not state_manager.change_zs3_id("missing", "*/8")
    assert len(zs3_signals) == 1


def test_reset_and_snapshot_load_send_it(state_manager, zs3_signals, zynthian_dirs):
    state_manager.save_zs3("*/1")
    path = str(zynthian_dirs["ZYNTHIAN_MY_DATA_DIR"] / "snapshots" / "zs3.zss")
    state_manager.save_snapshot(path)
    zs3_signals.clear()
    state_manager.reset_zs3()
    assert len(zs3_signals) == 1
    assert state_manager.load_snapshot(path) is not False
    assert len(zs3_signals) >= 2
    assert "*/1" in state_manager.get_zs3_ids()
