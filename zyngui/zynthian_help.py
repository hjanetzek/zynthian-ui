# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Help pages (zynthian-help): finding the page for a view, the index of all pages and the
# page's HTML with its includes resolved. UI-independent part of zynthian_gui.show_help and
# zynthian_gui_help, used by the Qt UI's help view.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import logging
from pathlib import Path

from zynconf import zynthian_paths

help_dir = zynthian_paths.help_dir


def find_file(fpath, layout_name):
    """The help file for fpath (as zynthian_gui.show_help's get_fpath): a path ("/" or "./" are
    the help directory) or a file name, looked up in the layout's directory, then in common.
    Returns the path, or None if there is no such file."""
    for b in ("/", "./"):
        if fpath.startswith(b):
            fpath = f"{help_dir}/{fpath[len(b):]}"
    p = Path(fpath).resolve()
    if p.exists():
        return str(p)
    for d in (layout_name, "common"):
        candidate = Path(f"{help_dir}/{d}/{p.name}")
        if candidate.exists():
            return str(candidate)
    return None


def _soup(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


def index(layout_name):
    """All help pages of the layout and common: [(title, path)], sorted by file name"""
    files = list(Path(f"{help_dir}/common").glob("*.html")) + \
        list(Path(f"{help_dir}/{layout_name}").glob("*.html"))
    files.sort(key=lambda f: f.name)
    items = []
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                soup = _soup(f)
            tag = soup.find("title") or soup.find("h1")
            title = tag.get_text(strip=True) if tag else file.stem
        except Exception as e:
            logging.warning(f"help page {file}: {e}")
            title = file.stem
        items.append((title, str(file)))
    return items


def page_html(fpath, proc_info=None, drop_classes=()):
    """The page's HTML (as zynthian_gui_help.load_file): w3-include-html divs replaced by the
    included file, the zynproc-info div by proc_info ("name: description") if given. Elements
    with one of drop_classes are removed (the knob diagrams, laid out by CSS a viewer may not
    have)."""
    with open(fpath, encoding="utf-8") as f:
        soup = _soup(f.read())
    for tag in soup.find_all("div", attrs={"id": "zynproc-info"}):
        if proc_info:
            tag.replace_with(_soup(f'<div class="note-block">{proc_info}</div>'))
        else:
            tag.decompose()
    for tag in soup.find_all("div", attrs={"w3-include-html": True}):
        try:
            with open(f"{help_dir}/include/{tag['w3-include-html']}", encoding="utf-8") as f:
                tag.replace_with(_soup(f.read()))
        except Exception:
            tag.decompose()
    for cls in drop_classes:
        for tag in soup.find_all(class_=cls):
            tag.decompose()
    return str(soup)
