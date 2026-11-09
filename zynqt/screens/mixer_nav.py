"""Keys, knobs and switches on the mixer, as zynthian_gui_mixer (arrow_*, switch_select, switch,
zynpot_cb, cuia_v5_zynpot_switch, back_action): left / right select the previous / next chain, up
/ down nudge its level, SELECT opens its chain control, bold SELECT its options. The mixer's view is
QML (MixerScreen); this is its screen object for ZynUI."""

from zyngui import zynthian_gui_config


class MixerNav:
    name = "mixer"

    def __init__(self, ui):
        self.ui = ui
        self.chain_manager = ui.chain_manager

    def build(self):
        pass

    def hide(self):
        pass

    def back(self):
        """BACK (zynthian_gui_mixer.back_action): the launcher (Tk toggles its launcher mode)"""
        self.ui.show_screen("launcher", history=False)
        return True

    def cuia_back(self, params=None):
        """BACK:B on the mixer: the chain manager (zynthian_gui_mixer.cuia_back)"""
        if params and str(params[0]).upper() == "B":
            self.ui.show_screen("chain_manager")
            return True
        return False

    def _mixer_ctrl(self, chain, symbol):
        if chain is None or not chain.zynmixer_proc:
            return None
        return chain.zynmixer_proc.controllers_dict.get(symbol)

    def _toggle(self, symbol):
        """Toggle the active chain's mute or toggle control (zynthian_gui_mixer strip
        toggle_mute / toggle_toggle)"""
        zctrl = self._mixer_ctrl(self.chain_manager.get_active_chain(), symbol)
        if zctrl is not None:
            zctrl.set_value(int(not zctrl.value))

    def switch(self, i, t):
        """The four switches (zynthian_gui_mixer.switch): 0 short the toggle control, 0 bold the
        chain manager, 1 bold the main menu, 2 short mute, 3 the select switch"""
        if i == 0:
            if t == "S":
                self._toggle(zynthian_gui_config.mixer_toggle)
                return True
            if t == "B":
                self.ui.show_screen("chain_manager")
                return True
        elif i == 1:
            if t == "B":
                self.ui.show_screen("main_menu")
                return True
        elif i == 2:
            if t == "S":
                self._toggle("mute")
                return True
        elif i == 3:
            return self.switch_select(t)
        return False

    def switch_select(self, t="S"):
        if t == "S":
            self.ui.chain_control()
        elif t == "B":
            self.item_menu()
        else:
            return False
        return True

    def item_menu(self):
        """Bold select (zynthian_gui_mixer.item_menu): the chain's options (Tk: chain control
        with its chain options subscreen)"""
        self.ui.show_screen("chain_options")

    def cuia_v5_zynpot_switch(self, params):
        """V5 knob pushes: 0 short toggle, 0 bold the chain's mixer controls, 1 short mute, 2 short
        add a chain, 2 bold move it, 3 the select switch"""
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            return False
        if i == 0:
            if t == "S":
                self._toggle(zynthian_gui_config.mixer_toggle)
                return True
            if t == "B":
                self.ui.chain_control()
                self.ui.chain_control_screen.select_mixer_processor()
                return True
        elif i == 1:
            if t == "S":
                self._toggle("mute")
                return True
        elif i == 2:
            if t == "S":
                self.ui.cuia_add_chain()
                return True
            if t == "B":
                self.ui.start_move_chain(stay=True)
                return False   # as Tk: falls through to the defaults (nothing for knob 2)
        elif i == 3:
            self.ui.switch_select(t)
            return True
        return False

    def zynpot(self, i, d):
        """Knobs (zynthian_gui_mixer.zynpot_cb): 0 the active chain's level, 1 its balance, 2
        the main level, 3 the chain selection"""
        cm = self.chain_manager
        if i == 0 or i == 1:
            zctrl = self._mixer_ctrl(cm.get_active_chain(), "level" if i == 0 else "balance")
            if zctrl is not None:
                zctrl.nudge(d)
        elif i == 2:
            zctrl = self._mixer_ctrl(cm.get_chain(0), "level")
            if zctrl is not None:
                zctrl.nudge(d)
        elif i == 3:
            cm.next_chain(d)
        return True

    def navigate(self, what):
        cm = self.chain_manager
        if what == "left":
            cm.previous_chain()
        elif what == "right":
            cm.next_chain()
        elif what in ("up", "down"):
            chain = cm.get_active_chain()
            if chain is not None and chain.zynmixer_proc:
                chain.zynmixer_proc.controllers_dict["level"].nudge(1 if what == "up" else -1)
        elif what == "select":
            self.ui.chain_control()
        elif what == "select_bold":
            self.item_menu()

    def zynpot_abs(self, i, val):
        """ZYNPOT_ABS (zynthian_gui_mixer.zynpot_abs): 0 the active chain's level, 1 its balance,
        2 the main level, 3 the main balance"""
        cm = self.chain_manager
        chain = cm.get_active_chain() if i < 2 else cm.get_chain(0)
        if chain is None or not chain.zynmixer_proc:
            return True
        ctrls = chain.zynmixer_proc.controllers_dict
        if i in (0, 2):
            ctrls["level"].set_value(val)
        elif i in (1, 3):
            ctrls["balance"].set_value(val * 2 - 1)
        return True
