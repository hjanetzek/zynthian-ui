"""The Qt screens' state for the websocket's "screen_state" feedback (zyngui.zynthian_websocket).

The messages are the Tk UI's: the screen under its Tk name, the title (the top bar's text, Tk's
select path) and the view state of the screens Tk reports one for, with Tk's keys and items:

  list screens         zyngui_selector {items, selected}; section titles as "> TITLE"
  engine               zyngui_engine {items, selected, categories {items, selected}}
  grid menus           zyngui_selector_grid {items, selected, columns}; empty cells ""
  chain_control        zyngui_chain_control {chain_blocks {items, selected} (only while the chain
                       is shown: select mode), zyngui_selector {items: the controller pages,
                       selected}}
  tempo, alsa_mixer,   zyngui_selector {items: the controller pages, selected} (Tk: its plain
  audio_player         control screen)
  confirm (overlay)    screen "confirm", zyngui_confirm {text}
  keyboard, help,      the screen name only (Tk: fullscreen modals without state)
  busy (loading)
  mixer, launcher, pattern_editor, chain_manager, midi_key_range, control_xy: screen and title
  only, as Tk.

ScreenStateWatch connects the Qt signals of the screens while someone is subscribed: any change
asks the feedback for the full state (cb_screen_state_full), which sends only what differs from
the state sent before, as Tk's partial updates do.
"""

import logging


def selector_items(entries, grid=False):
    """Item labels as Tk's: section titles with "> ", grid titles on one line (empty cells "")"""
    items = []
    for e in entries:
        title = str(e.get("title", ""))
        if grid:
            items.append(title.replace("\n", " "))
        elif e.get("separator") and title and not title.startswith("> "):
            items.append("> " + title)
        else:
            items.append(title)
    return items


class ListState:
    """A selector screen (zynqt.screens.base.SelectorScreen)"""

    def __init__(self, screen):
        self.screen = screen
        if screen.kind == "grid":
            self.state_key = "zyngui_selector_grid"
        elif screen.name == "engine":
            self.state_key = "zyngui_engine"
        else:
            self.state_key = "zyngui_selector"

    def get_state(self, what="all"):
        s = self.screen
        if what == "select":
            return {"selected": s.index}
        if s.kind == "grid":
            return {"items": selector_items(s.entries, grid=True), "selected": s.index, "columns": s.columns}
        state = {"items": selector_items(s.entries), "selected": s.index}
        if self.state_key == "zyngui_engine" and what == "all":
            state["categories"] = {"items": list(s.categories), "selected": s.categoryIndex}
        return state

    def title(self):
        return self.screen.title


class ControlState:
    """Chain control (zynqt.screens.control.ChainControl): Tk's chain_control (embedded: the chain
    blocks and the control screen's page list) or, for the special processors, its plain control
    screen (the page list)"""

    def __init__(self, cc, embedded=True):
        self.cc = cc
        self.state_key = "zyngui_chain_control" if embedded else "zyngui_selector"

    def pages(self):
        entries = self.cc.pages.entries
        if not entries:
            return {"items": ["NO PROCESSORS!"], "selected": 0}
        return {"items": selector_items(entries), "selected": self.cc.page}

    def get_state(self, what="all"):
        if self.state_key == "zyngui_selector":
            return self.pages()
        cc = self.cc
        state = {}
        if cc.selectMode and cc.isChain:
            nodes = cc.chainNodes
            state["chain_blocks"] = {"items": [n["title"].replace("\n", " ") for n in nodes],
                                     "selected": cc.chainNode}
        state["zyngui_selector"] = self.pages()
        return state

    def title(self):
        return self.cc.selectPath


class ConfirmState:
    state_key = "zyngui_confirm"

    def __init__(self, ui):
        self.ui = ui

    def get_state(self, what="all"):
        return {"text": self.ui.confirmText}

    def title(self):
        return ""


class TitleOnly:
    """A screen without view state: its title only"""
    state_key = None

    def __init__(self, title):
        self._title = title

    def get_state(self, what="all"):
        return {}

    def title(self):
        return self._title()


def current_state(ui):
    """(Tk screen name, state view) of what the Qt UI shows"""
    if ui.busy:
        return "loading", TitleOnly(lambda: "")
    if ui.confirmText:
        return "confirm", ConfirmState(ui)
    if ui.keyboardShown:
        return "keyboard", TitleOnly(lambda: "")
    if ui.helpShown:
        return "help", TitleOnly(lambda: "")
    name = ui.get_current_screen()
    cur = ui.current_screen
    screen = ui.list_screens.get(cur)
    if screen is not None:
        return name, ListState(screen)
    if cur == "chain_control":
        return name, ControlState(ui.chain_control_screen)
    if cur in ("tempo", "alsa_mixer", "audio_player"):
        return name, ControlState(ui.chain_control_screen, embedded=False)
    if cur in ("mixer", "launcher"):
        return name, TitleOnly(ui._snapshot_title)
    if cur == "pattern_editor":
        pe = ui.pattern_editor
        return name, TitleOnly(lambda: pe.modeTitle or pe.tkTitle)
    if cur == "chain_manager":
        return name, TitleOnly(lambda: chain_manager_title(ui.chain_manager_screen))
    if cur == "midi_key_range":
        return name, TitleOnly(lambda: ui.chain_control_screen.selectPath)
    return name, TitleOnly(lambda: "")


def chain_manager_title(cm):
    """As Main.qml screenTitle: "Chain: " and the selected column's chain"""
    try:
        return "Chain: " + cm.graph[cm.selection[0]]["rows"][0][0]["title"]
    except (IndexError, KeyError, TypeError):
        return "Chain Manager"


class ScreenStateWatch:
    """Connects the Qt signals that change the screen state to on_change while active"""

    def __init__(self, ui, on_change):
        self.ui = ui
        self.on_change = on_change
        self._connections = []

    def _connect(self, signal, slot):
        signal.connect(slot)
        self._connections.append((signal, slot))

    def start(self):
        if self._connections:
            return
        ui = self.ui
        changed = lambda *args: self.on_change()   # noqa: E731
        for sig in (ui.currentScreenChanged, ui.confirmChanged, ui.keyboardChanged, ui.helpChanged, ui.busyChanged):
            self._connect(sig, changed)

        def when_shown(*names):
            def slot(*args):
                if ui.current_screen in names:
                    self.on_change()
            return slot

        # The mixer's title: the snapshot (status, polled)
        self._connect(ui.statusChanged, when_shown("mixer", "launcher"))
        for name, screen in ui.list_screens.items():
            slot = when_shown(name)
            for sig in (screen.indexChanged, screen.titleChanged, screen.categoriesChanged,
                        screen.model.countChanged, screen.model.modelReset, screen.model.dataChanged):
                self._connect(sig, slot)
        cc = ui.chain_control_screen
        slot = when_shown("chain_control", "tempo", "alsa_mixer", "audio_player", "midi_key_range")
        for sig in (cc.processorsChanged, cc.pageChanged, cc.modeChanged, cc.selectPathChanged,
                    cc.pages.modelReset, cc.pages.dataChanged):
            self._connect(sig, slot)
        cm = ui.chain_manager_screen
        slot = when_shown("chain_manager")
        for sig in (cm.graphChanged, cm.selectionChanged):
            self._connect(sig, slot)
        pe = ui.pattern_editor
        slot = when_shown("pattern_editor")
        for sig in (pe.patternChanged, pe.modeChanged, pe.ccChanged):
            self._connect(sig, slot)

    def stop(self):
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError) as e:
                logging.debug(f"screen state: can't disconnect {signal} => {e}")
        self._connections = []
