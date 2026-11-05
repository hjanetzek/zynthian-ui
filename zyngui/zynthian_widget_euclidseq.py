# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Zynthian Widget Class for "Euclidean Sequencer"
#
# Copyright (C) 2025 Ronald Summers <ronfsum@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
# ******************************************************************************

from zynconf import zynthian_paths
import os
import sys
import math
import tkinter as tk
from tkinter import font as tkFont

# Zynthian specific modules
sys.path.append(f"{zynthian_paths.ui_dir}/")
from zyngui import zynthian_gui_config, zynthian_widget_base
from zyngui.zynthian_euclidseq_data import EuclidSeqModel


class zynthian_widget_euclidseq(zynthian_widget_base.zynthian_widget_base, tk.Frame):
    """
    Widget class for Euclidean Sequencer display.
    """
    def __init__(self, parent):
        tk.Frame.__init__(self, parent, bg="#000000")
        zynthian_widget_base.zynthian_widget_base.__init__(self, parent)

        # --- Early & Stable Attribute Initialization ---
        self.shown = False
        self.debug = True
        self.update_pending = False
        self.batch_update_after = 1

        # Sequencer state, OSC and patterns: zyngui.zynthian_euclidseq_data (shared with the Qt UI)
        self.model = EuclidSeqModel(on_change=self._model_changed)
        self.channels = self.model.channels
        self.zyngui = zynthian_gui_config.zyngui
        
        # --- UI Layout Dimensions ---
        self.canvas_width = 420
        self.canvas_height = 350 
        self.control_panel_width = 160
        self.scale = 2 

        self.graph_x = [4, 77, 150, 4, 77, 150]
        self.graph_y = [20, 20, 20, 110, 110, 110]

        self.x16 = [25, 31, 36, 39, 40, 39, 36, 31, 25, 19, 14, 11, 10, 11, 14, 19]  
        self.y16 = [10, 11, 14, 19, 25, 31, 36, 39, 40, 39, 36, 31, 25, 19, 14, 11]
        
        # --- Drag Interaction State Variables ---
        self.dragging_param = None
        self.dragging_note_ch = None # Specifically for tracking which circle is dragged
        self.drag_start_y = 0
        self.drag_last_y_for_threshold = 0
        self.drag_threshold = 15 
        self.did_drag = False


        # --- UI Widget Creation ---
        self.app_container = tk.Frame(self, bg="black")
        self.app_container.pack(expand=True, fill='both')

        self.sequencer_frame = tk.Frame(self.app_container, bg="black")
        self.sequencer_frame.pack(side=tk.LEFT, expand=True, fill='both', padx=5) 

        self.canvas = tk.Canvas(self.sequencer_frame, width=self.canvas_width, height=self.canvas_height, 
                               bg='black', highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)

        self.controls_frame = tk.Frame(self.app_container, bg="#181818", width=self.control_panel_width)
        self.controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,5), pady=5)
        self.controls_frame.pack_propagate(False) 

        self._create_control_panel_widgets()
        
        # Bind drag/click events to the main canvas
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.circle_hit_areas = []

        # --- OSC and Final Setup ---
        # MODIFIED: Removed manual OSC server creation. This will be handled by the Zynthian engine.
        self.processor = None

        

        self.draw_sequencer()
        self.update_animation()

    def set_processor(self, processor):
        self.processor = processor
        self.model.set_processor(processor)

    def handle_osc_message(self, path, args):
        return self.model.handle_osc_message(path, args)

    def _model_changed(self):
        self._update_control_panel_display()
        self.draw_sequencer()

    def _xy(self, k, ux, uy):
        """Canvas position of unit coordinates (model geometry) in channel k's circle"""
        r = 25 * self.scale
        return self.graph_x[k] * self.scale + r + ux * r, self.graph_y[k] * self.scale + r + uy * r

    def _get_scaled_euclidean_canvas_xy(self, model_x, model_y, base_x_for_channel, base_y_for_channel):
        MODEL_CENTER_COORD = 25.0
        MODEL_EFFECTIVE_RADIUS = 15.0
        TARGET_EFFECTIVE_RADIUS_UNITS = 25.0

        coord_rescale_factor = TARGET_EFFECTIVE_RADIUS_UNITS / MODEL_EFFECTIVE_RADIUS
        rel_x_model = model_x - MODEL_CENTER_COORD
        rel_y_model = model_y - MODEL_CENTER_COORD
        rescaled_rel_x = rel_x_model * coord_rescale_factor
        rescaled_rel_y = rel_y_model * coord_rescale_factor
        
        canvas_circle_center_x = base_x_for_channel + (TARGET_EFFECTIVE_RADIUS_UNITS * self.scale)
        canvas_circle_center_y = base_y_for_channel + (TARGET_EFFECTIVE_RADIUS_UNITS * self.scale)
        final_canvas_x = (rescaled_rel_x * self.scale) + canvas_circle_center_x
        final_canvas_y = (rescaled_rel_y * self.scale) + canvas_circle_center_y
        
        return final_canvas_x, final_canvas_y

    def _create_control_panel_widgets(self):
        self.control_widgets = {}
        parent = self.controls_frame
    
        label_font = tkFont.Font(family="TkFixedFont", size=10)
        button_font = tkFont.Font(family="TkFixedFont", size=10, weight="bold")
        channel_label_font = tkFont.Font(family="TkFixedFont", size=12, weight="bold")

        # Create Mode button first
        mode_frame = tk.Frame(parent, bg=parent["bg"])
        mode_frame.pack(fill=tk.X, pady=14)
        tk.Label(mode_frame, text="Mode:", font=label_font, fg="#cccccc", bg=parent["bg"], width=7, anchor="w").pack(side=tk.LEFT, padx=(0,10))
        mode_button = tk.Button(mode_frame, text="--", font=button_font, width=12, relief=tk.GROOVE,
                               bg="#333333", fg="#00ff00", activebackground="#444444", activeforeground="#00ff00")
        mode_button.pack(side=tk.LEFT, padx=(0,10))
        mode_button.bind("<ButtonPress-1>", lambda e: self._on_value_button_press(e, "mode"))
        mode_button.bind("<B1-Motion>", lambda e: self._on_value_button_drag(e, "mode"))
        mode_button.bind("<ButtonRelease-1>", lambda e: self._on_value_button_release(e, "mode"))
        self.control_widgets["mode"] = mode_button

        # Then create Channel label
        self.selected_channel_disp_label = tk.Label(parent, text=f"Channel: {self.model.select_ch + 1}", 
                                             font=channel_label_font, fg="white", bg=parent["bg"])
        self.selected_channel_disp_label.pack(pady=0)

        # Then create the remaining controls
        param_configs = [
            {"label": "Length", "key": "length"},
            {"label": "Hits", "key": "hits"},
            {"label": "Offset", "key": "offset"},
            {"label": "Interval", "key": "interval"}
        ]

        for config in param_configs:
            param_key = config['key']
            row_frame = tk.Frame(parent, bg=parent["bg"])
            row_frame.pack(fill=tk.X, pady=14)

            tk.Label(row_frame, text=f"{config['label']}:", font=label_font, fg="#cccccc", bg=parent["bg"], width=7, anchor="w").pack(side=tk.LEFT, padx=(0,10))
        
            value_button = tk.Button(row_frame, text="--", font=button_font, width=8, relief=tk.GROOVE,
                                     bg="#333333", fg="#00ff00", activebackground="#444444", activeforeground="#00ff00")
            value_button.pack(side=tk.LEFT, padx=(0,10))
        
            value_button.bind("<ButtonPress-1>", lambda e, k=param_key: self._on_value_button_press(e, k))
            value_button.bind("<B1-Motion>", lambda e, k=param_key: self._on_value_button_drag(e, k))
            value_button.bind("<ButtonRelease-1>", lambda e, k=param_key: self._on_value_button_release(e, k))
        
            self.control_widgets[param_key] = value_button
    
        self._update_control_panel_display()

        mute_button = tk.Button(parent, text="Mute", font=button_font, width=12, relief=tk.GROOVE,
                                bg="#552222", fg="white", activebackground="#663333")
        mute_button.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)       
        mute_button.bind("<Button-1>", lambda e: self.toggle_mute())
        self.control_widgets["mute"] = mute_button

    def _update_control_panel_display(self):
        if not hasattr(self, 'control_widgets'): return

        m = self.model
        self.selected_channel_disp_label.config(text=f"Channel: {m.select_ch + 1}")
        ch = m.select_ch

        self.control_widgets["mode"].config(text=m.display_mode.capitalize())
        self.control_widgets["length"].config(text=str(m.limit[ch]))
        self.control_widgets["hits"].config(text=str(m.hits[ch]))
        self.control_widgets["offset"].config(text=str(m.offset[ch]))

        interval_button = self.control_widgets["interval"]
        interval_row = interval_button.master
        if m.display_mode == "interval":
            interval_button.config(text=str(m.interval_value[ch]))
            interval_row.pack(fill=tk.X, pady=14)
        else:
            interval_row.pack_forget()

        mute_button = self.control_widgets.get("mute")
        if mute_button:
            if m.mute[ch]:
                mute_button.config(text="Unmute", bg="#225522")
            else:
                mute_button.config(text="Mute", bg="#552222")

    def on_canvas_press(self, event):
        x, y = event.x, event.y
        clicked_ch = None
        for i, (cx, cy, radius) in enumerate(self.circle_hit_areas):
            if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) <= radius:
                clicked_ch = i
                break
        
        if clicked_ch is not None:
            self.dragging_param = "note"
            self.dragging_note_ch = clicked_ch
            self.drag_start_y = event.y
            self.drag_last_y_for_threshold = event.y
            self.did_drag = False

    def on_canvas_drag(self, event):
        if self.dragging_param != "note": return
        self.did_drag = True

        delta_y = event.y - self.drag_last_y_for_threshold
        if abs(delta_y) >= self.drag_threshold:
            direction = -1 if delta_y > 0 else 1
            self.model.nudge_note(self.dragging_note_ch, direction)
            self.drag_last_y_for_threshold = event.y

    def on_canvas_release(self, event):
        if self.dragging_param == "note":
            if not self.did_drag:
                self.model.select_channel(self.dragging_note_ch)
            
            self.dragging_param = None
            self.dragging_note_ch = None
    
    def _on_value_button_press(self, event, param_key):
        self.dragging_param = param_key
        self.drag_start_y = event.y
        self.drag_last_y_for_threshold = event.y
        self.did_drag = False
        event.widget.config(relief=tk.SUNKEN, bg="#555555")

    def _on_value_button_drag(self, event, param_key):
        if self.dragging_param != param_key: return
        self.did_drag = True
        
        delta_y = event.y - self.drag_last_y_for_threshold
        if abs(delta_y) >= self.drag_threshold:
            direction = -1 if delta_y > 0 else 1
            self._adjust_param_value(param_key, direction)
            self.drag_last_y_for_threshold = event.y

    def _on_value_button_release(self, event, param_key):
        if self.dragging_param == param_key:
            if not self.did_drag:
                self._adjust_param_value(param_key, 1) # Treat click as a single increment
            
            event.widget.config(relief=tk.GROOVE, bg="#333333")
            self.dragging_param = None
    
    def _adjust_param_value(self, param_key, direction):
        self.model.adjust_param(param_key, direction)

    def toggle_mute(self):
        self.model.toggle_mute()

    def draw_sequencer(self):
        if self.update_pending: return
        self.update_pending = True
        self.after(self.batch_update_after, self.perform_draw)

    def perform_draw(self):
        if not self.shown: self.update_pending=False; return
        self.update_pending = False
        self.canvas.delete("all")
        self.calculate_circle_hit_areas()
        self.draw_step_dots()
        self.draw_hit_connections()
        self.draw_play_positions()
        self.draw_labels()
        self.canvas.update_idletasks()

    def draw_step_dots(self):
        for k in range(self.channels):
            for ux, uy in self.model.step_dots(k):
                x, y = self._xy(k, ux, uy)
                self.canvas.create_oval(x - 1, y - 1, x + 1, y + 1, fill="white", outline="white")

    def draw_hit_connections(self):
        r = 25 * self.scale
        for k in range(self.channels):
            coords = [self._xy(k, ux, uy) for ux, uy in self.model.hit_points(k)]
            cx, cy = self._xy(k, 0, 0)
            if len(coords) > 1:
                self.canvas.create_polygon(coords, fill="", outline="white", width=1)
            elif len(coords) == 1:
                self.canvas.create_line(cx, cy, coords[0][0], coords[0][1], fill="white", width=1)
            color = "yellow" if k == self.model.select_ch else "deepskyblue"
            for x, y in coords:
                self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)

    def draw_play_positions(self):
        for k in range(self.channels):
            pos = self.model.play_position(k)
            if pos is None:
                continue
            x, y = self._xy(k, pos[0], pos[1])
            if pos[2]:
                self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill="white", outline="white")
            else:
                self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, outline="white", width=2)

    def draw_labels(self):
        note_font = ("TkFixedFont", int(10 * self.scale / 1.5), "bold")
        radius = 25 * self.scale
        for k in range(self.channels):
            cx, cy = self._xy(k, 0, 0)
            if k == self.model.select_ch:
                size = 10 * self.scale * 0.8
                self.canvas.create_rectangle(cx - size, cy - size, cx + size, cy + size, fill="#555500",
                                             outline="yellow", width=2)
            self.canvas.create_text(cx, cy, text=f"{self.model.note_numbers[k]}", fill="#00FF00", font=note_font)
            self.canvas.create_text(cx, cy + radius - 115, text=f"Ch: {k + 1}", fill="red",
                                    font=("Arial", 16, "bold"))

    def calculate_circle_hit_areas(self):
        r=25*self.scale; self.circle_hit_areas=[(self.graph_x[k]*self.scale+r, self.graph_y[k]*self.scale+r,r) for k in range(self.channels)]

    def update_animation(self): self.after(50, self.update_animation)
    def show(self): self.shown=True; self.draw_sequencer()
    def hide(self): self.shown=False

# Main block for testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Euclidean Sequencer - Final UI")
    root.geometry("600x400")

    class MockZynthianGUIManager:
        def __init__(self): self.screens={'control':None}; self.main_tk=root
    zynthian_gui_config.zyngui = MockZynthianGUIManager()

    widget = zynthian_widget_euclidseq(root)
    widget.pack(expand=True, fill='both')
    widget.show()
    root.mainloop()
