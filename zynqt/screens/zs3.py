"""ZS3 (sub-snapshots: zynthian_gui_zs3, zynthian_gui_zs3_options): save, load, overwrite, rename,
clone, delete. Restore options, notes, moving and program change numbers are not ported yet."""

from zynqt.screens.base import NOT_PORTED, SelectorScreen, entry, separator


class ZS3(SelectorScreen):
    name = "zs3"

    def fill(self):
        sm = self.state_manager
        self.set_title("ZS3")
        entries = [entry("Save as new ZS3", data="SAVE_ZS3", icon="zs3_new.png",
                         info="Save current state as a new ZS3.")]
        index = None
        if "zs3-0" in sm.zs3:
            entries.append(entry("Default state", data="zs3-0", icon="zs3_default.png",
                                 info="Load default ZS3 state.\n\nLong press for options."))
        if len(sm.zs3) > 1:
            entries.append(separator("> SAVED ZS3s"))
        for zs3_id, state in sm.zs3.items():
            if zs3_id == "zs3-0":
                continue
            if zs3_id.startswith("zs3"):
                title = f"{state['title']}"
            else:
                parts = zs3_id.split('/')
                if len(parts) > 1:
                    if parts[0] == "*":
                        title = f"{state['title']} -> PRG#{parts[1]}"
                    else:
                        title = f"{state['title']} -> CH#{int(parts[0]) + 1}:PRG#{parts[1]}"
                else:
                    title = f"{state['title']} ({zs3_id})"
            if zs3_id == sm.last_zs3_id:
                index = len(entries)
            entries.append(entry(title, data=zs3_id, info="Restore ZS3.\n\nLong press for options."))
        self.set_entries(entries, index)

    def select_action(self, index, t):
        sm = self.state_manager
        zs3_id = self.entries[index]["data"]
        sm.disable_learn_pc()
        if t == "S":
            if zs3_id == "SAVE_ZS3":
                sm.save_zs3()
                self.fill()
            else:
                sm.load_zs3(zs3_id)
                self.ui.back()
        elif zs3_id != "SAVE_ZS3":
            self.show_options(zs3_id)

    def show_options(self, zs3_id):
        sm = self.state_manager
        title = sm.get_zs3_title(zs3_id)

        def done():
            self.fill()

        options = [("Overwrite", lambda: (sm.save_zs3(zs3_id), done()),
                    "Save current state, overwriting this ZS3.", "zs3_overwrite.png")]
        if zs3_id != "zs3-0":
            options += [
                ("Restore options...", lambda: self.ui.show_info(NOT_PORTED),
                 "Select which elements will be restored from this ZS3.", "zs3_settings.png"),
                ("Rename", lambda: self.ui.show_keyboard(lambda t: (sm.set_zs3_title(zs3_id, t), done()),
                                                          title, "Rename ZS3"),
                 "Rename this ZS3.", "zs3_rename.png"),
                ("Clone", lambda: self.ui.show_keyboard(lambda t: (sm.clone_zs3(zs3_id, t), done()),
                                                         title, "Name of the copy"),
                 "Copy this ZS3 to a new one, placed just after it.", "zs3_new.png"),
                ("Delete", lambda: self.ui.confirm(f"Do you really want to delete ZS3: {title}?",
                                                   lambda: (sm.delete_zs3(zs3_id), done())),
                 "Delete this ZS3.", "zs3_delete.png"),
            ]
        self.ui.show_options(title, options)
