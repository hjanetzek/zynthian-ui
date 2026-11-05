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
        self._shown = False
        ui.bridge.chainsChanged.connect(self._rebuild_if_shown)
        ui.bridge.snapshotLoaded.connect(self._rebuild_if_shown)
        ui.bridge.activeChainChanged.connect(self._active_chain)

    # Shown / hidden (ZynUI)

    def build(self):
        self._shown = True
        self._build()
        # Back from a node's screen: keep that node selected if it is still in the active chain
        node = self._node(self.selected)
        active = self.chain_manager.active_chain
        if node is None or active is None or node["chain_id"] != active.chain_id:
            self._select_active()
        else:
            self.selectionChanged.emit()

    def hide(self):
        self._shown = False

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
        for c, column in enumerate(self.nodes):
            for r, row in enumerate(column):
                for i, n in enumerate(row):
                    if proc is not None and n["proc"] is proc and n["chain_id"] == chain.chain_id:
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

    # After a move (ZynUI's move modes rebuild through this)

    def moved(self):
        self._build()
        self._select_active()
