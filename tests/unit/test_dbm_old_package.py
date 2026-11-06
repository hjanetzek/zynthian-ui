"""dbm_zynthian with a DrivenByMoss package from before the protocol check (no
drivenbymoss.protocol, e.g. drivenbymoss 26.1.0_p20261108): importing a dbm driver package raises
an ImportError (DbmProtocolError), which the ctrldev manager and pkgutil walks skip, not an
AttributeError."""

import importlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit


def test_old_package_import_raises_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "drivenbymoss", types.ModuleType("drivenbymoss"))
    monkeypatch.setitem(sys.modules, "dbm_host", types.ModuleType("dbm_host"))
    monkeypatch.delitem(sys.modules, "zyngine.ctrldev.dbm_zynthian", raising=False)
    with pytest.raises(ImportError, match="too old"):
        importlib.import_module("zyngine.ctrldev.dbm_zynthian")
    sys.modules.pop("zyngine.ctrldev.dbm_zynthian", None)
