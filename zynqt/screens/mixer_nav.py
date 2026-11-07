"""Keys on the mixer (zynthian_gui_mixer arrow_* / switch_select): left / right select the
previous / next chain, up / down nudge its level, SELECT opens its chain control, bold SELECT its
options. The mixer's view is QML (MixerScreen); this is its screen object for ZynUI."""


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
        return False

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
            self.ui.show_screen("chain_options")

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
