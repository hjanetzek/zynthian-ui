#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian GUI Admin Class
#
# Copyright (C) 2015-2024 Fernando Moyano <jofemodo@zynthian.org>
#
# ******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

from zynconf import zynthian_paths
import os
import re
import signal
import logging
from time import sleep
from threading import Thread
from curses import A_HORIZONTAL
from subprocess import check_output, Popen, PIPE, STDOUT

# Zynthian specific modules
import zynconf
import zynautoconnect
from zyncoder.zyncore import lib_zyncore
from zyngui import zynthian_gui_config
from zyngui.zynthian_gui_selector_info import zynthian_gui_selector_info
from zyngui import zynthian_admin_settings

# -------------------------------------------------------------------------------
# Zynthian Admin GUI Class
# -------------------------------------------------------------------------------


class zynthian_gui_admin(zynthian_gui_selector_info):

    data_dir = zynthian_paths.data_dir
    sys_dir = zynthian_paths.sys_dir

    def __init__(self):
        self.commands = None
        self.thread = None
        self.child_pid = None

        self.last_action = None
        self.update_available = False
        self.refresh_wifi_thread = None
        self.refresh_wifi = False
        self.wifi_index = -1
        self.wifi_status = "???"
        self.filling_list = False

        super().__init__('Action')

        self.state_manager = self.zyngui.state_manager

        if not zynconf.desktop_mode and self.state_manager.allow_rbpi_headphones():
            self.default_rbpi_headphones()

    def refresh_status(self):
        if self.shown:
            super().refresh_status()
            if not self.filling_list and self.update_available != self.state_manager.update_available:
                self.update_available = self.state_manager.update_available
                self.update_list()

    def refresh_wifi_task(self):
        while self.refresh_wifi:
            self.wifi_status = zynconf.get_nwdev_status_string("wlan0")
            if not self.filling_list and self.wifi_index > 0:
                wifi_item = f"Wi-Fi Config ({self.wifi_status})"
                if self.listbox.get(self.wifi_index) != wifi_item:
                    self.listbox.delete(self.wifi_index)
                    self.listbox.insert(self.wifi_index, wifi_item)
            sleep(2)

    def build_view(self):
        self.update_available = self.state_manager.update_available
        if not self.refresh_wifi_thread and not zynconf.desktop_mode:
            self.refresh_wifi = True
            self.refresh_wifi_thread = Thread(target=self.refresh_wifi_task, name="wifi_refresh")
            self.refresh_wifi_thread.start()
        res = super().build_view()
        self.state_manager.check_for_updates()
        return res

    def hide(self):
        self.refresh_wifi = False
        self.refresh_wifi_thread = None
        super().hide()

    def fill_list(self):
        if self.filling_list:
            return

        self.filling_list = True
        self.list_data = []

        self.list_data.append((None, 0, "> MIDI"))
        #self.list_data.append((self.zyngui.midi_in_config, 0, "MIDI Input Devices", ["Configure MIDI input devices.", "midi_input.png"]))
        #self.list_data.append((self.zyngui.midi_out_config, 0, "MIDI Output Devices", ["Configure MIDI output devices.", "midi_output.png"]))
        # self.list_data.append((self.midi_profile, 0, "MIDI Profile"))

        info_txt = "MIDI Program Change messages can be used for learning/recalling ZS3s (subsnapshots) or for changing processor presets."
        if zynthian_gui_config.midi_prog_change_zs3:
            self.list_data.append((self.toggle_prog_change_zs3, 0, "Program Change => ZS3", [info_txt, "midi_settings.png"]))
        else:
            self.list_data.append((self.toggle_prog_change_zs3, 0, "Program Change => Processor Presets", [info_txt, "midi_settings.png"]))
            if zynthian_gui_config.midi_bank_change:
                self.list_data.append((self.toggle_bank_change, 0, "\u2612 MIDI Bank Change",
                                       ["Select bank when MIDI Program Change received", "midi_settings.png"]))
            else:
                self.list_data.append((self.toggle_bank_change, 0, "\u2610 MIDI Bank Change",
                                       ["Don't select bank when MIDI Program Change received", "midi_settings.png"]))

        gtrans = lib_zyncore.get_global_transpose()
        if gtrans > 0:
            display_val = f"+{gtrans}"
        elif gtrans == 0:
            display_val = "None"
        else:
            display_val = f"{gtrans}"
        self.list_data.append((self.edit_global_transpose, 0, f"Global Transpose ({display_val})",
                               ["MIDI note transpose.\nThis effects all MIDI messages and is in addition to individual chain transpose.", "midi_settings.png"]))

        info_txt = "Send active MIDI channel messages to all chains with the same MIDI channel. When disabled, only active chain receives."
        if lib_zyncore.get_active_midi_chan():
            self.list_data.append((self.toggle_active_midi_channel, 0, "\u2612 Active MIDI channel", [info_txt, "midi_settings.png"]))
        else:
            self.list_data.append((self.toggle_active_midi_channel, 0, "\u2610 Active MIDI channel", [info_txt, "midi_settings.png"]))

        if zynthian_gui_config.midi_usb_by_port:
            self.list_data.append((self.toggle_usbmidi_by_port, 0, "\u2612 MIDI-USB mapped by port",
                                   ["MIDI ports are indexed by their device name and the physical USB port to which they are plugged", "midi_settings.png"]))
        else:
            self.list_data.append((self.toggle_usbmidi_by_port, 0, "\u2610 MIDI-USB mapped by port",
                                   ["MIDI ports are indexed by their device name only.", "midi_settings.png"]))

        if zynthian_gui_config.midi_chanpress_cc:
            display_val = str(zynthian_gui_config.midi_chanpress_cc)
        else:
            display_val = "NONE"
        self.list_data.append((self.set_chanpress_cc, 0, f"Channel Pressure => CC ({display_val})",
                               ["Map channel pressure messages (monoAT) to the selected CC.", "midi_settings.png"]))
        self.list_data.append((self.test_midi, 0, "Test MIDI",
                               ["Play a MIDI track to test MIDI output.\n\nThis will play the MIDI through any loaded chains.", "midi_output.png"]))

        self.list_data.append((None, 0, "> AUDIO"))

        #self.list_data.append((self.audio_levels, 0, "Audio Levels", ["Show audio levels view.", "meters.png"]))
        self.list_data.append((self.pfl, 0, f"PFL Output ({zynthian_gui_config.pfl_output})", ["Select the audio output device for pre-fader listening.", "headphones.png"]))
        self.list_data.append((self.show_tts, 0, "ZynVoice", ["Text to speech accessibility options", "audio_options.png"]))
        if not zynconf.desktop_mode and self.state_manager.allow_rbpi_headphones():
            if zynthian_gui_config.rbpi_headphones:
                self.list_data.append((self.stop_rbpi_headphones, 0, "\u2612 RBPi Headphones",
                                       ["RBPi onboard headphone output (Lo-Fi) is enabled", "headphones.png"]))
            else:
                self.list_data.append((self.start_rbpi_headphones, 0, "\u2610 RBPi Headphones",
                                       ["RBPi onboard headphone output (Lo-Fi) is disabled", "headphones.png"]))

        self.list_data.append((self.hotplug_audio_menu, 0, "Hotplug USB Audio",
                               ["Configure hotplug USB audio interfaces.\nWhen enabled, USB audio interfaces will be detected and available. The main audio interface, that must always remain connected, is not included, nor the interface used for ZynVoice.", "audio_options.png"]))

        if zynthian_gui_config.snapshot_mixer_settings:
            self.list_data.append((self.toggle_snapshot_mixer_settings, 0, "\u2612 Audio Levels on Snapshots",
                                   ["Soundcard parameters are saved with snapshot", "meter.png"]))
        else:
            self.list_data.append((self.toggle_snapshot_mixer_settings, 0, "\u2610 Audio Levels on Snapshots",
                                   ["Soundcard parameters are not saved with snapshot", "meter.png"]))

        if zynthian_gui_config.enable_dpm:
            self.list_data.append((self.toggle_dpm, 0, "\u2612 Mixer Peak Meters",
                                   ["Peak programme meters are enabled.", "meters.png"]))
        else:
            self.list_data.append((self.toggle_dpm, 0, "\u2610 Mixer Peak Meters",
                                   ["Peak programme meters are disabled.\nThis saves a little CPU power.", "meters.png"]))
        self.list_data.append((self.test_audio, 0, "Test Audio",
                               ["Play an audio track to test audio output.\n\nPress BACK to cancel playback.", "audio_output.png"]))

        self.list_data.append((None, 0, "> NETWORK"))

        self.list_data.append((self.network_info, 0, "Network Info",
                               ["Show network details, e.g. IP address, etc.", "network.png"]))
        # On a desktop, Wi-Fi, VNC and Bluetooth are managed by the host system
        if not zynconf.desktop_mode:
            self.list_data.append((self.wifi_config, 0, f"Wi-Fi Config ({self.wifi_status})",
                                   ["Configure Wi-Fi connections.", "wifi.png"]))
            self.wifi_index = len(self.list_data) - 1
            if zynconf.is_service_active("vncserver0"):
                self.list_data.append((self.state_manager.stop_vncserver, 0, "\u2612 VNC Server",
                                       ["Display zynthian UI and processors' native GUI via VNC.\n This uses more CPU. It is advised to disable during performance.", "network.png"]))
            else:
                self.list_data.append((self.state_manager.start_vncserver, 0, "\u2610 VNC Server",
                                       ["Display zynthian UI and processors' native GUI via VNC.\n This uses more CPU. It is advised to disable during performance.", "network.png"]))
            self.list_data.append((self.bluetooth, 0, "Bluetooth",
                                   ["Scan, enable and configure Bluetooth devices.\n\nMust enable Bluetooth here to access BLE MIDI devices. Also supports HID devices.", "bluetooth.png"]))

        self.list_data.append((None, 0, "> USER INTERFACE"))
        self.list_data.append((self.visible_chains, 0, f"Visible Chains ({zynthian_gui_config.visible_mixer_strips})",
                               ["Quantity of chains shown in mixer", "settings.png"]))
        self.list_data.append((self.visible_launchers, 0, f"Visible Launchers ({zynthian_gui_config.visible_launchers})",
                               ["Quantity of launchers shown in mixer", "settings.png"]))
        self.list_data.append((self.mixer_toggle, 0, f"Mixer Toggle Control ({zynthian_gui_config.mixer_toggle})",
                               ["The toggle control to show at top of each mixer channel", "settings.png"]))
        if zynthian_gui_config.preset_preload:
            self.list_data.append((self.toggle_preset_preload, 0, "\u2612 Preset Preload",
                                   ["Pre-load presets while browsing the list", "settings.png"]))
        else:
            self.list_data.append((self.toggle_preset_preload, 0, "\u2610 Preset Preload",
                                   ["Do not pre-load preset for while browsing the list", "settings.png"]))
        #if not zynthian_gui_config.wiring_layout.startswith("V5"):
        match zynthian_gui_config.touch_navigation:
            case "v5_keypad_left":
                touch_navigation_option = "V5 keypad at Left"
            case "v5_keypad_right":
                touch_navigation_option = "V5 keypad at right"
            case _:
                touch_navigation_option = "None"
        self.list_data.append((self.touch_navigation_menu, 0, f"Touch Navigation: {touch_navigation_option}", ["Enable touch-screen V5 buttons.", "settings.png"]))
        #if self.zyngui.capture_log_fname:
        #    self.list_data.append((self.workflow_capture_stop, 0, "\u2612 Capture Workflow", ["End workflow capture session", "capture.png"]))
        #else:
        #    self.list_data.append((self.workflow_capture_start, 0, "\u2610 Capture Workflow",
        #       ["Start workflow capture session.\n\nZynthian's display, audio output, encoder and button actions are saved to file until this option is deselected.", "capture.png"]))
        self.list_data.append((None, 0, "> SCREEN"))
        if "brightness_config" in self.zyngui.screens and self.zyngui.screens["brightness_config"].get_num_zctrls() > 0:
            self.list_data.append((self.zyngui.brightness_config, 0, "Brightness",
                                   ["Adjust display and LED brightness.", "bright_settings.png"]))
        if not zynconf.desktop_mode:  # Writes the system's X11 configuration
            self.list_data.append((self.zyngui.calibrate_touchscreen, 0, "Calibrate Touchscreen",
                                   ["Show touchscreen calibration.\nTouch each crosshair until it changes color.\nScreen closes after 15s of inactivity.",
                                    "settings.png"]))
        self.list_data.append((self.zyngui.cuia_screen_clean, 0, "Clean Screen",
                               ["10s countdown with no touch trigger. Allows screen to be cleaned without triggering any action.", "settings.png"]))

        self.list_data.append((None, 0, "> SYSTEM"))
        len_check = len(self.list_data)
        if "cv_config" in self.zyngui.screens:
            self.list_data.append((self.show_cv_config, 0, "CV Settings",
                                   ["Control Voltage configuration.", "settings.png"]))
        if self.state_manager.update_available:
            self.list_data.append((self.update_software, 0, "Update Software",
                                   ["Updates software from Internet.\n\nThis option is only shown when updates are availale (\u21bb icon in the topbar).\nDon't poweroff while updating!", "update.png"]))
        # self.list_data.append((self.update_system, 0, "Update Operating System"))
        if zynthian_gui_config.control_test_enabled:
            self.list_data.append((self.control_test, 0, "Test control HW",
                                   ["Test system hardware.", "settings.png"]))
        # self.list_data.append((None, 0, "> POWER"))
        # self.list_data.append((self.restart_gui, 0, "Restart UI"))
        if zynthian_gui_config.debug_thread:
            self.list_data.append((self.exit_to_console, 0, "Exit",
                                   ["Stop zynthian UI but do not reboot.", "poweroff.png"]))
        #self.list_data.append((self.power, 0, "Power",
        #                       ["Turn off or reboot zynthian.\n\nPower is still fed to the device but it is effectively off.", "poweroff.png"]))
        if len(self.list_data) == len_check:
            self.list_data.pop() # Remove section title for empty section

        super().fill_list()
        self.filling_list = False

    def select_action(self, i, t='S'):
        if self.list_data[i][0]:
            self.last_action = self.list_data[i][0]
            self.last_action()

    def set_select_path(self):
        self.select_path.set("Admin")
        # TODO: Should not need to set title and select_path!
        self.set_title("Admin")

    def execute_commands(self):
        self.state_manager.start_busy("admin_commands")
        error_counter = 0
        for cmd in self.commands:
            logging.info("Executing Command: %s" % cmd)
            self.zyngui.add_info("EXECUTING:\n", "EMPHASIS")
            self.zyngui.add_info("{}\n".format(cmd))
            try:
                self.proc = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
                self.zyngui.add_info("RESULT:\n", "EMPHASIS")
                for line in self.proc.stdout:
                    if re.search("ERROR", line, re.IGNORECASE):
                        error_counter += 1
                        tag = "ERROR"
                    elif re.search("Already", line, re.IGNORECASE):
                        tag = "SUCCESS"
                    else:
                        tag = None
                    logging.info(line.rstrip())
                    self.zyngui.add_info(line, tag)
                self.zyngui.add_info("\n")
            except Exception as e:
                logging.error(e)
                self.zyngui.add_info("ERROR: %s\n" % e, "ERROR")

        if error_counter > 0:
            logging.info("COMPLETED WITH {} ERRORS!".format(error_counter))
            self.zyngui.add_info("COMPLETED WITH {} ERRORS!".format(error_counter), "WARNING")
        else:
            logging.info("COMPLETED OK!")
            self.zyngui.add_info("COMPLETED OK!", "SUCCESS")

        self.commands = None
        self.zyngui.add_info("\n\n")
        self.zyngui.hide_info_timer(5000)
        self.state_manager.end_busy("admin_commands")

    def start_command(self, cmds):
        if not self.commands:
            logging.info("Starting Command Sequence")
            self.commands = cmds
            self.thread = Thread(target=self.execute_commands, args=())
            self.thread.name = "command sequence"
            self.thread.daemon = True  # thread dies with the program
            self.thread.start()

    def killable_execute_commands(self):
        # self.state_manager.start_busy("admin commands")
        for cmd in self.commands:
            logging.info("Executing Command: %s" % cmd)
            self.zyngui.add_info("EXECUTING:\n", "EMPHASIS")
            self.zyngui.add_info("{}\n".format(cmd))
            try:
                proc = Popen(cmd.split(" "), stdout=PIPE, stderr=PIPE)
                self.child_pid = proc.pid
                self.zyngui.add_info("\nPID: %s" % self.child_pid)
                (output, error) = proc.communicate()
                self.child_pid = None
                if error:
                    result = "ERROR: %s" % error
                    logging.error(result)
                    self.zyngui.add_info(result, "ERROR")
                if output:
                    logging.info(output)
                    self.zyngui.add_info(output)
            except Exception as e:
                result = "ERROR: %s" % e
                logging.error(result)
                self.zyngui.add_info(result, "ERROR")

        self.commands = None
        self.zyngui.hide_info_timer(5000)
        # self.state_manager.end_busy("admin commands")

    def killable_start_command(self, cmds):
        if not self.commands:
            logging.info("Starting Command Sequence")
            self.commands = cmds
            self.thread = Thread(target=self.killable_execute_commands, args=())
            self.thread.name = "killable command sequence"
            self.thread.daemon = True  # thread dies with the program
            self.thread.start()

    def kill_command(self):
        if self.child_pid:
            logging.info("Killing process %s" % self.child_pid)
            os.kill(self.child_pid, signal.SIGTERM)
            self.child_pid = None
            if self.last_action == self.test_midi:
                self.state_manager.all_sounds_off()

    # ------------------------------------------------------------------------------
    # CONFIG OPTIONS
    # ------------------------------------------------------------------------------

    def audio_levels(self, t='S'):
        logging.info("Audio Levels")
        self.zyngui.show_screen("alsa_mixer")

    def pfl(self, t='S'):
        logging.info("PFL routing")
        self.enable_param_editor(self, "PFL Output",
                {'labels': zynthian_admin_settings.pfl_output_labels(), 'value': zynthian_gui_config.pfl_output},
                self.pfl_cb)

    def pfl_cb(self, value):
        zynthian_admin_settings.set_pfl_output(self.param_editor_zctrl.get_value2label(value))
        self.update_list()

    def show_tts(self, t='S'):
        logging.info("Text To Speech")
        self.zyngui.show_screen("tts")

    def start_rbpi_headphones(self, save_config=True):
        logging.info("STARTING RBPI HEADPHONES")
        try:
            check_output("systemctl start headphones", shell=True)
            zynthian_gui_config.rbpi_headphones = 1
            # Update Config
            if save_config:
                zynconf.save_config({
                    "ZYNTHIAN_RBPI_HEADPHONES": str(zynthian_gui_config.rbpi_headphones)
                })
            # Call autoconnect after a little time
            zynautoconnect.request_audio_connect()
        except Exception as e:
            logging.error(e)

        self.update_list()

    def stop_rbpi_headphones(self, save_config=True):
        logging.info("STOPPING RBPI HEADPHONES")

        try:
            check_output("systemctl stop headphones", shell=True)
            zynthian_gui_config.rbpi_headphones = 0
            # Update Config
            if save_config:
                zynconf.save_config({
                    "ZYNTHIAN_RBPI_HEADPHONES": str(int(zynthian_gui_config.rbpi_headphones))
                })

        except Exception as e:
            logging.error(e)

        self.update_list()

    # Start/Stop RBPI Headphones depending on configuration
    def default_rbpi_headphones(self):
        if zynthian_gui_config.rbpi_headphones:
            self.start_rbpi_headphones(False)
        else:
            self.stop_rbpi_headphones(False)

    def get_hotplug_menu_options(self):
        options = {}
        self.hotplug_devices = {}
        for label, action, device, info in zynthian_admin_settings.hotplug_options():
            options[label] = [action, [info, None]] if action else None
            self.hotplug_devices[label] = device
        return options

    def hotplug_audio_menu(self):
        self.zyngui.screens['option'].config("Hotplug Audio", self.get_hotplug_menu_options(), self.hotplug_audio_cb, False)
        self.zyngui.show_screen('option')

    def hotplug_audio_cb(self, option, value):
        if value == "tts":
            self.show_tts()
            return
        zynthian_admin_settings.hotplug_apply(value, self.hotplug_devices.get(option), self.zyngui.state_manager)
        self.zyngui.screens['option'].config("Hotplug Audio", self.get_hotplug_menu_options(), self.hotplug_audio_cb, False)
        self.zyngui.show_screen('option')

    def toggle_dpm(self):
        zynthian_admin_settings.toggle_dpm()
        self.update_list()

    def visible_chains(self):
        self.enable_param_editor(self, "Visible chains",
                                 {'value_min': 4, 'value_max': 16, 'value': zynthian_gui_config.visible_mixer_strips},
                                 self.visible_chains_cb)

    def visible_launchers(self):
        self.enable_param_editor(self, "Visible launchers",
                                 {'value_min': 4, 'value_max': 16, 'value': zynthian_gui_config.visible_launchers},
                                 self.visible_launchers_cb)

    def mixer_toggle(self):
        self.enable_param_editor(self, "Toggle Control",
                                 {'labels': zynthian_admin_settings.MIXER_TOGGLES, 'value': zynthian_gui_config.mixer_toggle},
                                 self.mixer_toggle_cb)

    def toggle_snapshot_mixer_settings(self):
        zynthian_admin_settings.toggle_snapshot_mixer_settings()
        self.update_list()

    def toggle_preset_preload(self):
        zynthian_admin_settings.toggle_preset_preload()
        self.update_list()

    def bluetooth(self):
        self.zyngui.show_screen("bluetooth")

    def touch_navigation_menu(self):
        self.zyngui.screens['option'].config("Touch Navigation",
                                             {"None": "",
                                              "V5 keypad at left": "v5_keypad_left",
                                              "V5 keypad at right": "v5_keypad_right"},
                                             self.touch_navigation_cb,
                                             True)
        self.zyngui.show_screen('option')

    def touch_navigation_cb(self, option, value):
        if value != zynthian_gui_config.touch_navigation:
            self.zyngui.show_confirm("Restart UI to apply touch-navigation settings?",
                                     self.touch_navigation_cb_confirmed, value)

    def touch_navigation_cb_confirmed(self, value=""):
        zynconf.save_config({"ZYNTHIAN_UI_TOUCH_NAVIGATION": value})
        self.restart_gui()

    def visible_chains_cb(self, value):
        zynthian_admin_settings.set_visible_mixer_strips(value)
        self.zyngui.screens["mixer"].update_layout()
        self.update_list()

    def visible_launchers_cb(self, value):
        zynthian_admin_settings.set_visible_launchers(value)
        self.zyngui.screens["mixer"].update_layout()
        self.update_list()

    def mixer_toggle_cb(self, value):
        zynthian_admin_settings.set_mixer_toggle(self.param_editor_zctrl.value2label[str(value)])
        self.update_list()

    # -------------------------------------------------------------------------
    # Global Transpose editing
    # -------------------------------------------------------------------------

    def edit_global_transpose(self):
        self.enable_param_editor(self, "Global Transpose",
                                 {'value_min': -24, 'value_max': 24, 'value': lib_zyncore.get_global_transpose()})

    # -------------------------------------------------------------------------
    # Setting Channel Pressure => CC
    # -------------------------------------------------------------------------

    def set_chanpress_cc(self):
        val = zynthian_gui_config.midi_chanpress_cc
        if val is None:
           val = 0
        self.enable_param_editor(self, "Channel Pressure => CC",
                                 {'value_min': 0, 'value_max': 119, 'value': val},
                                 self.set_chanpress_cc_cb)

    def set_chanpress_cc_cb(self, value):
        zynthian_admin_settings.set_chanpress_cc(value, self.state_manager)
        self.update_list()

    # -------------------------------------------------------------------------
    # Param Editor knob action
    # -------------------------------------------------------------------------

    def send_controller_value(self, zctrl):
        """ Handle param editor value change """

        if zctrl.symbol == "Global Transpose":
            transpose = zctrl.value
            lib_zyncore.set_global_transpose(transpose)
            self.update_list()

    # -------------------------------------------------------------------------

    def toggle_active_midi_channel(self):
        zynthian_admin_settings.toggle_active_midi_channel()
        self.update_list()

    def toggle_usbmidi_by_port(self):
        zynthian_admin_settings.toggle_usbmidi_by_port()
        self.update_list()

    def toggle_prog_change_zs3(self):
        zynthian_admin_settings.toggle_prog_change_zs3()
        self.update_list()

    def toggle_bank_change(self):
        zynthian_admin_settings.toggle_bank_change()
        self.update_list()

    def show_cv_config(self):
        self.zyngui.show_screen("cv_config")

    def midi_profile(self):
        logging.info("MIDI Profile")
        self.zyngui.show_screen("midi_profile")

    # ------------------------------------------------------------------------------
    # NETWORK INFO
    # ------------------------------------------------------------------------------

    def wifi_config(self):
        self.zyngui.show_screen("wifi")

    def network_info(self):
        self.zyngui.show_info("NETWORK INFO\n")

        res = zynconf.network_info()
        for k, v in res.items():
            self.zyngui.add_info(" {} => {}\n".format(k, v[0]), v[1])

        if self.zyngui.tts:
            timeout = 12000
        else:
            timeout = 5000
        self.zyngui.hide_info_timer(timeout)
        self.zyngui.state_manager.end_busy("gui_admin")

    # ------------------------------------------------------------------------------
    # TEST FUNCTIONS
    # ------------------------------------------------------------------------------

    def test_audio(self):
        logging.info("TESTING AUDIO")
        self.zyngui.show_info("TEST AUDIO")
        # self.killable_start_command(["mpg123 {}/audio/test.mp3".format(self.data_dir)])
        self.killable_start_command(
            [f"mplayer -nogui -noconsolecontrols -nolirc -nojoystick -really-quiet -ao jack {self.data_dir}/files/Audio/Oya.mp3"])
        zynautoconnect.request_audio_connect()

    def test_midi(self):
        logging.info("TESTING MIDI")
        self.state_manager.toggle_midi_playback(f"{self.data_dir}/files/Midi/roland_take5.mid")
        self.zyngui.show_screen("midi_recorder")

    def control_test(self, t='S'):
        logging.info("TEST CONTROL HARDWARE")
        self.zyngui.show_screen_reset("control_test")

    # ------------------------------------------------------------------------------
    # SYSTEM FUNCTIONS
    # ------------------------------------------------------------------------------

    def debug(self):
        breakpoint()

    def workflow_capture_start(self):
        self.zyngui.start_capture_log()
        self.zyngui.close_screen()

    def workflow_capture_stop(self):
        self.zyngui.stop_capture_log()
        self.update_list()

    def update_software(self):
        logging.info("UPDATE SOFTWARE")
        self.last_state_action()
        self.zyngui.show_info("UPDATE SOFTWARE")
        self.zyngui.add_info("Checking for Internet... ")
        if os.system("ping -c1 -W1 github.com"):
            self.zyngui.add_info("ERROR: Cannot reach GitHub", "ERROR")
            self.zyngui.hide_info_timer(5000)
            return
        self.zyngui.add_info("SUCCESS\n", "SUCCESS")
        self.start_command([self.sys_dir + "/scripts/update_zynthian.sh"])
        self.state_manager.update_available = False
        self.update_available = False

    def update_system(self):
        logging.info("UPDATE SYSTEM")
        self.last_state_action()
        self.zyngui.show_info("UPDATE SYSTEM")
        self.start_command([self.sys_dir + "/scripts/update_system.sh"])

    def restart_gui(self):
        logging.info("RESTART ZYNTHIAN-UI")
        self.zyngui.show_splash("Restarting UI")
        self.last_state_action()
        self.zyngui.exit(102)

    def exit_to_console(self):
        logging.info("EXIT TO CONSOLE")
        self.zyngui.show_splash("Exiting")
        self.last_state_action()
        self.zyngui.exit(101)

    def power(self):
        self.zyngui.screens["grid_sel"].setup("Power", [
            {"icon": "cancel.png", "title": "Cancel", "action": self.zyngui.close_screen},
            {"icon": "poweroff.png", "title": "Shutdown", "action": self.power_off_confirmed},
            {"icon": "reboot.png", "title": "Reboot", "action": self.reboot_confirmed}
        ], cols=3)
        self.zyngui.show_screen("grid_sel")

    def reboot_confirmed(self, params=None):
        logging.info("REBOOT")
        self.zyngui.show_splash("Rebooting...")
        self.last_state_action()
        self.zyngui.exit(100)

    def power_off_confirmed(self, params=None):
        logging.info("POWER OFF")
        self.zyngui.show_splash("Shutting down...")
        self.last_state_action()
        self.zyngui.exit(0)

    def last_state_action(self):
        if zynthian_gui_config.restore_last_state:
            self.state_manager.save_last_state_snapshot()
        else:
            self.state_manager.delete_last_state_snapshot()
        try:
            zynconf.save_config({"ZYNTHIAN_TOUCH_SHOWN": zynthian_gui_config.touch_shown})
        except Exception as e:
            logging.warning(f"Failed to save touch shown config: {e}")
        if self.zyngui.tts:
            self.zyngui.tts._tts.announce_disable = True

# ------------------------------------------------------------------------------
