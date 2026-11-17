"""Port descriptions of LV2 plugins (zynthian_lv2.get_plugin_ports), cached per plugin URI, and the
jalv engine's controllers built from them.

A throw-away LV2_PATH holds a fake plugin (TTL only: lilv doesn't need the binary to describe ports).
Needs the real lilv binding: skipped where tests/bootstrap.py had to stub it.
"""

import os
import types

import pytest

pytestmark = pytest.mark.integration

PLUGIN_URI = "urn:zyntest:ports"

MANIFEST = """\
@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<{uri}> a lv2:Plugin ; lv2:binary <plugin.so> ; rdfs:seeAlso <plugin.ttl> .
"""

PLUGIN_TTL = """\
@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .
@prefix doap: <http://usefulinc.com/ns/doap#> .
<{uri}> a lv2:Plugin, lv2:InstrumentPlugin ; doap:name "Ports" ;
  lv2:port [ a lv2:InputPort, lv2:ControlPort ; lv2:index 0 ; lv2:symbol "cutoff" ; lv2:name "Cutoff" ;
             lv2:default 0.5 ; lv2:minimum 0.0 ; lv2:maximum 1.0 ] ,
           [ a lv2:InputPort, lv2:ControlPort ; lv2:index 1 ; lv2:symbol "wave" ; lv2:name "Wave" ;
             lv2:portProperty lv2:integer, lv2:enumeration ; lv2:default 0 ; lv2:minimum 0 ; lv2:maximum 1 ;
             lv2:scalePoint [ rdfs:label "Saw" ; rdf:value 0 ] , [ rdfs:label "Square" ; rdf:value 1 ] ]
           {extra} .
"""

EXTRA_PORT = """, [ a lv2:InputPort, lv2:ControlPort ; lv2:index 2 ; lv2:symbol "gain" ; lv2:name "Gain" ;
             lv2:default 1.0 ; lv2:minimum 0.0 ; lv2:maximum 2.0 ]"""


def write_plugin(bundle, extra=""):
    (bundle / "manifest.ttl").write_text(MANIFEST.format(uri=PLUGIN_URI))
    ttl = PLUGIN_TTL.format(uri=PLUGIN_URI, extra=extra)
    (bundle / "plugin.ttl").write_text("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
                                       "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n" + ttl)


@pytest.fixture
def lv2(tmp_path, monkeypatch):
    from tests.bootstrap import STUBBED_MODULES
    if "lilv" in STUBBED_MODULES:
        pytest.skip("needs the lilv binding (stubbed here)")
    from zyngine import zynthian_lv2 as z
    system = tmp_path / "system"
    bundle = system / "ports.lv2"
    bundle.mkdir(parents=True)
    write_plugin(bundle)
    monkeypatch.setenv("LV2_PATH", str(system))
    monkeypatch.setattr(z, "LV2_STAMP_FILE", str(tmp_path / "lv2.stamp"))
    z.init_lilv()
    yield types.SimpleNamespace(z=z, bundle=bundle, tmp=tmp_path)
    monkeypatch.undo()
    z.init_lilv()


def test_ports_are_described(lv2):
    ports = {p["symbol"]: p for p in lv2.z.get_plugin_ports(PLUGIN_URI)}
    assert set(ports) == {"cutoff", "wave"}
    assert ports["cutoff"]["range"] == {"default": 0.5, "min": 0.0, "max": 1.0}
    assert [sp["label"] for sp in ports["wave"]["scale_points"]] == ["Saw", "Square"]


def test_lilv_is_queried_once_per_plugin(lv2, monkeypatch):
    calls = []
    orig = lv2.z._get_plugin_ports
    monkeypatch.setattr(lv2.z, "_get_plugin_ports", lambda url: calls.append(url) or orig(url))
    lv2.z.plugin_ports_cache.clear()
    first = lv2.z.get_plugin_ports(PLUGIN_URI)
    second = lv2.z.get_plugin_ports(PLUGIN_URI)
    assert calls == [PLUGIN_URI]
    assert first == second


def test_callers_get_their_own_copy(lv2):
    first = lv2.z.get_plugin_ports(PLUGIN_URI)
    first[0]["name"] = "changed"
    first[0]["range"]["max"] = 99
    first[1]["scale_points"].clear()
    second = lv2.z.get_plugin_ports(PLUGIN_URI)
    assert second[0]["name"] != "changed"
    assert second[0]["range"]["max"] == 1.0
    assert len(second[1]["scale_points"]) == 2


def test_cache_is_dropped_when_lv2_data_is_reloaded(lv2):
    assert len(lv2.z.get_plugin_ports(PLUGIN_URI)) == 2
    write_plugin(lv2.bundle, EXTRA_PORT)
    # an install or update touches the stamp file (or the LV2_PATH folders) => check_lv2_changes reloads
    (lv2.tmp / "lv2.stamp").write_text("")
    os.utime(lv2.tmp / "lv2.stamp", ns=(1, 1))
    assert lv2.z.check_lv2_changes()
    assert [p["symbol"] for p in lv2.z.get_plugin_ports(PLUGIN_URI)] == ["cutoff", "wave", "gain"]


def make_engine(cls):
    engine = cls.__new__(cls)
    engine.plugin_url = PLUGIN_URI
    engine.plugin_name = "Ports"
    engine.type = "MIDI Synth"
    return engine


def test_jalv_instances_get_their_own_controllers(lv2):
    from zyngine.zynthian_engine_jalv import zynthian_engine_jalv
    one = make_engine(zynthian_engine_jalv)
    two = make_engine(zynthian_engine_jalv)
    ctrls1 = one.get_lv2_controllers_dict()
    ctrls2 = two.get_lv2_controllers_dict()
    assert set(ctrls1) == set(ctrls2) == {"cutoff", "wave"}
    for symbol in ctrls1:
        assert ctrls1[symbol] is not ctrls2[symbol]
        assert ctrls1[symbol].engine is one and ctrls2[symbol].engine is two
    assert ctrls1["wave"].labels is not ctrls2["wave"].labels
    ctrls1["cutoff"].value = 0.9
    ctrls1["wave"].labels[0] = "changed"
    assert ctrls2["cutoff"].value == 0.5
    assert ctrls2["wave"].labels[0] == "Saw"
    # a third instance after the changes still starts from the plugin's defaults
    ctrls3 = make_engine(zynthian_engine_jalv).get_lv2_controllers_dict()
    assert ctrls3["cutoff"].value == 0.5 and ctrls3["wave"].labels == ["Saw", "Square"]
