"""Chain manager (zynthian_gui_chain_manager): all chains as columns of nodes (chain options, MIDI
input, processors, outputs), from the graph shared with the Tk UI (zyngui.zynthian_chain_graph).
Tap opens the node (chain options, routing, processor options), long press moves the chain or
processor; arrows move the selection, SEL opens, bold SEL moves."""

from PySide6.QtCore import QObject, Property, Signal, Slot

from zyngui.zynthian_chain_graph import build_chain_graph, node_kind


class ChainManager(QObject):
    name = "chain_manager"

    graphChanged = Signal()
    selectionChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.chain_manager = ui.chain_manager
        self.nodes = []
        self._graph = []
        self._pinned = 0
        self.selected = [0, 0, 0]
        self._last_proc = None      # the current processor when last hidden
        self._shown = False
        ui.bridge.chainsChanged.connect(self._rebuild_if_shown)
        ui.bridge.snapshotLoaded.connect(self._rebuild_if_shown)
        ui.bridge.activeChainChanged.connect(self._active_chain)

    # Shown / hidden (ZynUI)

    def build(self):
        self._shown = True
        self._build()
        # Back from a node's screen: keep that node selected if it is still in the active chain
        # (Tk's build_view: also when the current processor changed since it was last shown)
        node = self._node(self.selected)
        active = self.chain_manager.active_chain
        if node is None or active is None or node["chain_id"] != active.chain_id \
                or getattr(self.ui, "current_processor", None) is not self._last_proc:
            self._select_active()
        else:
            self.selectionChanged.emit()

    def hide(self):
        self._shown = False
        self._last_proc = getattr(self.ui, "current_processor", None)

    def _rebuild_if_shown(self):
        if self._shown:
            self._build()
            self._select_active()

    def _build(self):
        self.nodes, _ = build_chain_graph(self.chain_manager)
        active = self.chain_manager.active_chain
        self._pinned = self.chain_manager.get_pinned_pos()
        graph = []
        for chain_idx, column in enumerate(self.nodes):
            rows = []
            for row in column:
                rows.append([{"title": n["title"], "kind": node_kind(n),
                              "bypassed": bool(not isinstance(n["proc"], str) and n["proc"].is_bypassed()),
                              "isDst": n["is_dst"]} for n in row])
            chain_id = column[0][0]["chain_id"]
            graph.append({"chainId": chain_id, "rows": rows, "pinned": chain_idx >= self._pinned,
                          "active": bool(active and active.chain_id == chain_id)})
        self._graph = graph
        self.graphChanged.emit()

    def _active_chain(self):
        if not self._shown:
            return
        # Another chain became active (mixer, CUIA): its column highlighted, its header selected
        active = self.chain_manager.active_chain
        for col in self._graph:
            col["active"] = bool(active and active.chain_id == col["chainId"])
        self.graphChanged.emit()
        node = self._node(self.selected)
        if active and (node is None or node["chain_id"] != active.chain_id):
            self._select_active()

    def _select_active(self):
        """Select the active chain's current processor, or its chain options node"""
        chain = self.chain_manager.active_chain
        if chain is None or not self.nodes:
            return
        proc = getattr(self.ui, "current_processor", None)
        # The current processor, else (the audio player, ...: not in the graph) the chain's own
        # current processor, as Tk's select_node
        for p in (proc, chain.current_processor):
            for c, column in enumerate(self.nodes):
                for r, row in enumerate(column):
                    for i, n in enumerate(row):
                        if p is not None and n["proc"] is p and n["chain_id"] == chain.chain_id:
                            self._set_selected([c, r, i])
                            return
        idx = self.chain_manager.get_chain_index(chain.chain_id)
        if idx is not None and 0 <= idx < len(self.nodes):
            self._set_selected([idx, 0, 0])

    # For QML

    @Property("QVariantList", notify=graphChanged)
    def graph(self):
        return self._graph

    @Property("QVariantList", notify=selectionChanged)
    def selection(self):
        return list(self.selected)

    # Selection

    def _node(self, pos):
        try:
            c, r, i = pos
            return self.nodes[c][r][i]
        except (IndexError, TypeError, ValueError):
            return None

    def _set_selected(self, pos):
        if self._node(pos) is None:
            return
        self.selected = list(pos)
        self.selectionChanged.emit()

    def select_node(self, pos):
        """Select a node: its chain becomes active, a processor the current processor"""
        node = self._node(pos)
        if node is None:
            return
        self._set_selected(pos)
        if self.chain_manager.active_chain is None or self.chain_manager.active_chain.chain_id != node["chain_id"]:
            self.chain_manager.set_active_chain_by_id(node["chain_id"])
        if not isinstance(node["proc"], str):
            self.ui.set_current_processor(node["proc"])

    @Slot(int, int, int)
    def tapNode(self, c, r, i):
        self.select_node([c, r, i])
        self.activate("S")

    @Slot(int, int, int)
    def longPressNode(self, c, r, i):
        self.select_node([c, r, i])
        self.activate("B")

    def activate(self, t):
        node = self._node(self.selected)
        if node is None:
            return
        proc = node["proc"]
        if t == "B":
            if proc == "chain_options":
                if node["chain_id"] != 0:
                    self.ui.start_move_chain(stay=True)
                else:
                    self.ui.show_screen("chain_options")
            elif not isinstance(proc, str):
                if self.chain_manager.can_move_processor(proc):
                    self.ui.start_move_processor(proc, stay=True)
                else:
                    self.ui.show_info("This processor can't be moved.")
            return
        match proc:
            case "chain_options":
                self.ui.show_screen("chain_options")
            case "midi_input":
                self.ui.show_screen("midi_in")
            case "midi_output":
                self.ui.show_screen("midi_out")
            case "audio_out" | "audio_in":
                self.ui.show_screen(proc)
            case str():
                pass
            case _:
                self.ui.show_screen("processor_options")

    def move_selection(self, what):
        if not self.nodes:
            return
        c, r, i = self.selected
        if what in ("up", "down"):
            r += -1 if what == "up" else 1
            if not 0 <= r < len(self.nodes[c]):
                return
            i = min(i, len(self.nodes[c][r]) - 1)
        else:
            step = -1 if what == "left" else 1
            if 0 <= i + step < len(self.nodes[c][r]):
                i += step   # parallel processors first
            else:
                c += step
                if not 0 <= c < len(self.nodes):
                    return
                r = min(r, len(self.nodes[c]) - 1)
                i = 0 if step > 0 else len(self.nodes[c][r]) - 1
        self.select_node([c, r, i])

    def navigate(self, what):
        if what in ("up", "down", "left", "right"):
            self.move_selection(what)
        elif what == "select":
            self.activate("S")
        elif what == "select_bold":
            self.activate("B")

    def back(self):
        return False

    # Knobs and switches (zynthian_gui_chain_manager)

    def _select_offset(self, d):
        """Knob 2: through the nodes of the chain (parallel ones, then the next row)"""
        if not self.nodes:
            return
        c, r, i = self.selected
        i += d
        if i >= len(self.nodes[c][r]):
            r += 1
            if r >= len(self.nodes[c]):
                return
            i = 0
        elif i < 0:
            r -= 1
            if r < 0:
                return
            i = len(self.nodes[c][r]) - 1
        self.select_node([c, r, i])

    def zynpot(self, i, d):
        if self.ui.movingChain or self.ui.movingProcessor:
            return False    # ZynUI's move modes take the select knob
        if i == 2:
            self._select_offset(1 if d > 0 else -1)
            return True
        if i == 3:
            self.move_selection("right" if d > 0 else "left")
            return True
        return False

    def switch(self, i, t):
        """Switch 1 bold the main menu, 2 short add a chain"""
        if i == 1 and t == "B":
            self.ui.show_screen("main_menu")
            return True
        if i == 2 and t == "S":
            self.ui.cuia_add_chain()
            return True
        return False

    def cuia_v5_zynpot_switch(self, params):
        """Knob 2 bold: the active chain's options; else as the switches"""
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            return False
        if i == 2 and t == "B":
            self.ui.show_screen("chain_options")
            return True
        return self.switch(i, t)

    # After a move (ZynUI's move modes rebuild through this)

    def moved(self):
        self._build()
        self._select_active()
