"""zyngui/zynthian_cuia_list.py: the CUIA names (and categories) without the UI.

* The list matches the Tk UI's ``cuia_*`` methods (and aliases), in the order of ``dir()``, and the categories
  the "Category:" lines of their docstrings,
  so ``zynthian_gui.get_cuia_list()`` returns what it returned when it walked ``dir(cls)``.
* The Qt UI (``zynqt/ui.py``, where it exists) handles the same CUIAs (its ZYNSWITCH / ZYNPOT are
  ``cuia__zynswitch`` / ``cuia__zynpot``, called from its CUIA thread).
* The module imports in a fresh interpreter in which tkinter, PIL and websocket_server can't be
  imported, and without loading libzyncore (zynthian-webconf imports it next to any UI, or none).
  ``zyngui/__init__`` imports ``zynthian_gui_config`` (zynconf, the zyncoder wrapper), so these
  come along; the other zyngui modules must not.

Static analysis (``ast``) for the UIs: nothing of them is imported.
"""

import ast
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from zyngui import zynthian_cuia_list  # noqa: E402

# Qt's names for the CUIAs it handles in its CUIA thread
QT_PRIVATE = {"_ZYNSWITCH": "ZYNSWITCH", "_ZYNPOT": "ZYNPOT"}


def class_cuia_methods(path, class_name):
    """The cuia_* method names (defs and ``cuia_x = cuia_y`` aliases) of the class."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            names = set()
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(item.name)
                elif isinstance(item, ast.Assign):
                    names.update(t.id for t in item.targets if isinstance(t, ast.Name))
            return sorted(n for n in names if n.startswith("cuia_"))
    raise AssertionError(f"no class {class_name} in {path}")


def test_list_matches_tk_methods():
    methods = class_cuia_methods(REPO / "zyngui" / "zynthian_gui.py", "zynthian_gui")
    expected = [m[5:].upper() for m in methods]  # as get_cuia_list() did over dir(cls)
    listed = list(zynthian_cuia_list.CUIA_LIST)
    assert set(listed) == set(expected), (
        f"zynthian_cuia_list.CUIA_LIST differs from zynthian_gui's cuia_* methods: "
        f"missing {sorted(set(expected) - set(listed))}, extra {sorted(set(listed) - set(expected))}")
    assert listed == expected, "CUIA_LIST is not in dir() order (sorted by the lower case method name)"
    assert len(listed) == len(set(listed))


def class_cuia_categories(path, class_name):
    """{CUIA name: category} from the "Category:" line of the cuia_* docstrings; aliases take their target's."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name)
    cats, aliases = {}, {}
    for item in cls.body:
        if isinstance(item, ast.FunctionDef) and item.name.startswith("cuia_"):
            m = re.search(r"^\s*Category:\s*(\w+)", ast.get_docstring(item) or "", re.M)
            if m:
                cats[item.name[5:].upper()] = m.group(1)
        elif isinstance(item, ast.Assign) and isinstance(item.value, ast.Name):
            for t in item.targets:
                if isinstance(t, ast.Name) and t.id.startswith("cuia_"):
                    aliases[t.id[5:].upper()] = item.value.id[5:].upper()
    for alias, target in aliases.items():
        if target in cats:
            cats[alias] = cats[target]
    return cats


def test_categories_match_tk_docstrings():
    expected = class_cuia_categories(REPO / "zyngui" / "zynthian_gui.py", "zynthian_gui")
    listed = zynthian_cuia_list.get_cuia_categories()
    assert listed == expected, (
        f"zynthian_cuia_list.CUIA_CATEGORIES differs from the docstrings: "
        f"{sorted(set(listed.items()) ^ set(expected.items()))}")
    assert set(listed) <= set(zynthian_cuia_list.CUIA_LIST)
    assert set(listed.values()) <= set(zynthian_cuia_list.CUIA_CATEGORY_NAMES)


def test_qt_ui_handles_the_same_cuias():
    path = REPO / "zynqt" / "ui.py"
    if not path.exists():
        pytest.skip("no Qt UI in this tree")
    qt = {QT_PRIVATE.get(m[5:].upper(), m[5:].upper()) for m in class_cuia_methods(path, "ZynUI")}
    listed = set(zynthian_cuia_list.CUIA_LIST)
    assert qt == listed, (
        f"the Qt UI's CUIAs differ from the list: not in Qt {sorted(listed - qt)}, "
        f"Qt only {sorted(qt - listed)}")


def test_imports_without_the_ui_dependencies():
    code = (
        "import sys\n"
        "for m in ('tkinter', 'PIL', 'websocket_server', 'zyngine', 'zynqt', 'PySide6'):\n"
        "    sys.modules[m] = None\n"
        "from zyngui.zynthian_cuia_list import get_cuia_list\n"
        "l = get_cuia_list()\n"
        "assert 'SCREEN_ADMIN' in l, l\n"
        "ok = ('zyngui.zynthian_cuia_list', 'zyngui.zynthian_gui_config')\n"
        "assert not [m for m in sys.modules if m.startswith('zyngui.') and m not in ok], sorted(sys.modules)\n"
        "from zyncoder import zyncore\n"
        "assert zyncore.lib_zyncore is None\n"
        "print(len(l))\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    assert int(res.stdout) == len(zynthian_cuia_list.CUIA_LIST)
