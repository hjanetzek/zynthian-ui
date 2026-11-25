"""A chain's controller pages, the model of its Chain Controllers (zyngine.zynthian_zctrl_pages,
docs/chain-controller-pages.md): slots as (processor id, symbol) references resolved when used,
assign / move / remove, the toggle's next free slot, pages, purge after a processor is removed,
the flat view (chain.zctrls), upstream's dense list, the chain's state."""

from types import SimpleNamespace

from zyngine.zynthian_zctrl_pages import SLOTS, ZctrlPages, zctrl_ref


class Proc:
    def __init__(self, pid, symbols):
        self.id = pid
        self.controllers_dict = {s: SimpleNamespace(symbol=s, processor=self) for s in symbols}


class Chain:
    def __init__(self, procs):
        self.procs = procs

    def get_processors(self):
        return list(self.procs)


def setup():
    synth = Proc(1, ["cutoff", "reso", "attack", "decay", "sustain", "release"])
    mixer = Proc(2, ["level", "balance"])
    chain = Chain([synth, mixer])
    return chain, synth, mixer, ZctrlPages(chain)


def z(proc, symbol):
    return proc.controllers_dict[symbol]


def test_pages_have_four_slots():
    assert SLOTS == 4


def test_no_pages_by_default():
    chain, synth, mixer, rp = setup()
    assert rp.pages == [] and rp.current_page() == -1 and rp.find(z(synth, "cutoff")) == []
    assert rp.flat() == () and rp.dense_refs() == []


def test_assign_creates_the_first_page_and_resolves():
    chain, synth, mixer, rp = setup()
    assert rp.assign(z(synth, "cutoff"), 0, 2) == 0
    assert rp.pages[0].name == "Controllers 1"
    assert rp.pages[0].slots[2] == (1, "cutoff")
    zs = rp.zctrls(0)
    assert len(zs) == SLOTS and zs[2] is z(synth, "cutoff") and zs[0] is None
    assert rp.find(z(synth, "cutoff")) == [(0, 2)]


def test_assign_to_a_new_page():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    assert rp.assign(z(mixer, "level"), 1, 0) == 1
    assert [p.name for p in rp.pages] == ["Controllers 1", "Controllers 2"]
    assert rp.assign(z(mixer, "level"), 5, 0) == -1     # not the next page
    assert rp.assign(z(mixer, "level"), 0, 4) == -1     # no slot 5


def test_assign_on_the_same_page_moves_and_swaps():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    rp.assign(z(synth, "reso"), 0, 1)
    rp.assign(z(synth, "cutoff"), 0, 1)
    assert rp.pages[0].slots[:2] == ((1, "reso"), (1, "cutoff"))
    rp.assign(z(synth, "cutoff"), 0, 3)
    assert rp.pages[0].slots[1] is None and rp.pages[0].slots[3] == (1, "cutoff")


def test_assign_flat_counts_from_a_page_and_creates_pages():
    """The JAM's row of 8: slots 0-3 the base page, 4-7 the next one"""
    chain, synth, mixer, rp = setup()
    assert rp.assign_flat(z(synth, "cutoff"), 6, base=0) == 1
    assert len(rp.pages) == 2 and rp.pages[1].slots[2] == (1, "cutoff")
    assert rp.assign_flat(z(synth, "reso"), 1, base=1) == 1
    assert rp.pages[1].slots[1] == (1, "reso")
    assert rp.assign_flat(None, 7, base=1) == -1 and len(rp.pages) == 2     # a clear creates nothing
    assert rp.assign_flat(None, 2, base=1) == 1 and rp.pages[1].slots[2] is None


def test_a_controller_may_be_on_several_pages():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    rp.assign(z(synth, "cutoff"), 1, 3)
    assert rp.find(z(synth, "cutoff")) == [(0, 0), (1, 3)]
    assert rp.remove(z(synth, "cutoff"), page=1)
    assert rp.find(z(synth, "cutoff")) == [(0, 0)]
    assert rp.remove(z(synth, "cutoff"))
    assert rp.find(z(synth, "cutoff")) == [] and len(rp.pages) == 2


def test_assign_none_clears_a_slot():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 3)
    assert rp.assign(None, 0, 3) == 0
    assert rp.pages[0].slots[3] is None


def test_a_controller_without_processor_is_refused():
    chain, synth, mixer, rp = setup()
    assert rp.assign(SimpleNamespace(symbol="x", processor=None), 0, 0) == -1
    assert rp.add_next(SimpleNamespace(symbol="x", processor=None)) is None
    assert rp.pages == []
    assert zctrl_ref(None) is None


def test_toggle_adds_to_the_first_free_slot_from_page_one():
    chain, synth, mixer, rp = setup()
    for s in ("cutoff", "reso", "attack", "decay", "sustain"):
        assert rp.toggle(z(synth, s))
    assert [p.name for p in rp.pages] == ["Controllers 1", "Controllers 2"]
    assert rp.pages[1].slots == ((1, "sustain"), None, None, None)
    rp.current = 1      # the current page doesn't matter
    assert not rp.toggle(z(synth, "reso"))      # off: a gap, the others stay
    assert rp.pages[0].slots == ((1, "cutoff"), None, (1, "attack"), (1, "decay"))
    assert rp.toggle(z(mixer, "level"))         # the gap first
    assert rp.pages[0].slots[1] == (2, "level")
    assert rp.add_next(z(mixer, "level")) == (0, 1)     # already there


def test_a_missing_reference_is_not_a_free_slot():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "attack"), 0, 0)
    synth.controllers_dict.pop("attack")
    assert rp.add_next(z(synth, "cutoff")) == (0, 1)


def test_toggle_all_full_makes_a_new_page():
    chain, synth, mixer, rp = setup()
    for s in ("cutoff", "reso", "attack", "decay"):
        rp.toggle(z(synth, s))
    rp.rename_page(0, "Perform")
    assert rp.add_next(z(mixer, "level")) == (1, 0)
    assert rp.pages[1].name == "Controllers 2"


def test_toggle_off_deletes_empty_default_named_last_pages():
    chain, synth, mixer, rp = setup()
    for s in ("cutoff", "reso", "attack", "decay", "sustain"):
        rp.toggle(z(synth, s))
    rp.toggle(z(synth, "sustain"))
    assert len(rp.pages) == 1
    for s in ("cutoff", "reso", "attack", "decay"):
        rp.toggle(z(synth, s))
    assert rp.pages == [] and rp.flat() == ()


def test_toggle_off_keeps_named_and_inner_pages():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    rp.assign(z(synth, "reso"), 1, 0)
    rp.rename_page(1, "Mine")
    rp.toggle(z(synth, "cutoff"))       # an inner empty page stays
    rp.toggle(z(synth, "reso"))         # a renamed one too
    assert [p.name for p in rp.pages] == ["Controllers 1", "Mine"]
    rp.rename_page(1, "Controllers 2")
    rp.prune()                          # both empty and default-named now
    assert rp.pages == []


def test_missing_references_are_kept_and_come_back():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "attack"), 0, 0)
    attack = synth.controllers_dict.pop("attack")       # a preset without it
    assert rp.zctrls(0)[0] is None and rp.pages[0].slots[0] == (1, "attack")
    assert rp.dense_refs() == []
    synth.controllers_dict["attack"] = attack
    assert rp.zctrls(0)[0] is attack


def test_purge_clears_removed_processors():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    rp.assign(z(mixer, "level"), 0, 1)
    chain.procs.remove(synth)
    rp.purge()
    assert rp.pages[0].slots[:2] == (None, (2, "level"))


def test_flat_view_is_positional():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 1)
    rp.assign(z(mixer, "level"), 1, 2)
    rp.add_page()
    assert rp.flat() == (None, z(synth, "cutoff"), None, None, None, None, z(mixer, "level"))
    assert rp.dense_refs() == [[1, "cutoff"], [2, "level"]]


def test_from_dense_makes_pages_of_four():
    """Upstream's chain controllers (a snapshot's "zctrls") as pages"""
    chain, synth, mixer, rp = setup()
    rp.from_dense([[1, "cutoff"], [1, "reso"], [2, "level"], [1, "attack"], [2, "balance"], ["bad"]])
    assert [p.name for p in rp.pages] == ["Controllers 1", "Controllers 2"]
    assert rp.flat() == (z(synth, "cutoff"), z(synth, "reso"), z(mixer, "level"), z(synth, "attack"),
                         z(mixer, "balance"))
    rp.from_dense([])
    assert rp.pages == []


def test_pages_rename_move_delete_and_current():
    chain, synth, mixer, rp = setup()
    for i in range(3):
        rp.add_page()
    assert [p.name for p in rp.pages] == ["Controllers 1", "Controllers 2", "Controllers 3"]
    assert rp.rename_page(1, "Perform") and not rp.rename_page(1, "")
    rp.set_shown(1)
    assert rp.current == 1 and rp.shown == 1
    assert rp.move_page(1, -1) == 0
    assert [p.name for p in rp.pages] == ["Perform", "Controllers 1", "Controllers 3"]
    assert rp.current == 0 and rp.shown is None
    assert rp.move_page(2, -5) == 0 and rp.current == 1
    assert rp.delete_page(1)
    assert rp.current == 1 and [p.name for p in rp.pages] == ["Controllers 3", "Controllers 1"]
    assert rp.default_name() == "Controllers 4"   # (count + 1, the next free)
    rp.set_shown(None)
    assert rp.shown is None
    rp.clear()
    assert rp.pages == [] and rp.current == 0


def test_state_round_trip():
    chain, synth, mixer, rp = setup()
    rp.assign(z(synth, "cutoff"), 0, 0)
    rp.assign(z(mixer, "level"), 1, 3)
    rp.rename_page(1, "Mix")
    rp.current = 1
    state = rp.get_state()
    assert state[0] == {"name": "Controllers 1", "slots": [[1, "cutoff"], None, None, None]}
    other = ZctrlPages(chain)
    other.set_state(state, 1)
    assert [p.name for p in other.pages] == ["Controllers 1", "Mix"]
    assert other.zctrls(1)[3] is z(mixer, "level") and other.current == 1
    other.set_state([{"name": "Bad", "slots": [[1]]}, {"slots": []}], 9)
    assert [p.name for p in other.pages] == ["Controllers 1"] and other.current == 0
