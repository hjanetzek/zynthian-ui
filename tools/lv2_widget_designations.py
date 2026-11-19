#!/usr/bin/env python3
"""List the installed LV2 plugins whose control ports carry the designations that select
zynthian's envelope, filter or drawbar widgets (zynthian_lv2.get_plugin_ports), and the plugins
with a zyngui:widget UI. See docs/zynthian-widgets.md.

Runs on the device (needs py3-lilv; reads every bundle, a few seconds), e.g. from the host:

    ssh -p 2252 user@127.0.0.1 'cat > /tmp/d.py' < tools/lv2_widget_designations.py
    ssh -p 2252 user@127.0.0.1 'LV2_PATH=/usr/lib/lv2:/usr/share/zynthian/zynthian-ui/lv2 python3 /tmp/d.py'

(LV2_PATH: add zynthian-ui's lv2/ and the user widget folder to see the zyngui:widget UIs.)
Output: TSV  kind  plugin-uri  plugin-name  port-group  designations(symbol=param,...);
kind: envelope, filter, drawbar or zyngui. Counts and other param: designations on stderr."""
import sys
import lilv

PARAM = "http://lv2plug.in/ns/ext/parameters#"
ENV = ["delay", "attack", "hold", "decay", "sustain", "fade", "release"]
FLT = ["cutoffFrequency", "resonance"]
ZYNGUI_WIDGET = "http://zynthian.org/ns/lv2/zyngui#widget"

w = lilv.World()
w.load_all()
ns_lv2 = lilv.Namespace(w, "http://lv2plug.in/ns/lv2core#")
ns_pg = lilv.Namespace(w, "http://lv2plug.in/ns/ext/port-groups#")
counts = {}
other = {}
for p in w.get_all_plugins():
    uri = str(p.get_uri())
    name = str(p.get_name())
    found = []
    for i in range(p.get_num_ports()):
        port = p.get_port_by_index(i)
        if not (port.is_a(lilv.LILV_URI_INPUT_PORT) and port.is_a(lilv.LILV_URI_CONTROL_PORT)):
            continue
        d = port.get(ns_lv2.designation)
        if d is None:
            continue
        d = str(d)
        g = port.get(ns_pg.group)
        g = str(g).rsplit("#", 1)[-1].rsplit("/", 1)[-1] if g is not None else "-"
        sym = str(port.get_symbol())
        if d.startswith(PARAM):
            short = d[len(PARAM):]
            if short in ENV:
                found.append(("envelope", g, f"{sym}={short}"))
            elif short in FLT:
                found.append(("filter", g, f"{sym}={short}"))
            elif short == "drawbar":
                found.append(("drawbar", g, f"{sym}={short}"))
            else:
                other[short] = other.get(short, 0) + 1
    kinds = {}
    for k, g, s in found:
        kinds.setdefault(k, {}).setdefault(g, []).append(s)
    for k, groups in kinds.items():
        counts[k] = counts.get(k, 0) + 1
        for g, syms in groups.items():
            print(f"{k}\t{uri}\t{name}\t{g}\t{','.join(syms)}")
    try:
        c_uis = lilv.c.plugin_get_uis(p.plugin)
        uis = lilv.UIs(p.world, c_uis) if c_uis else []
        for ui in uis:
            if ui.is_a(w.new_uri(ZYNGUI_WIDGET)):
                print(f"zyngui\t{uri}\t{name}\t-\t{ui.get_uri()} -> {ui.get_binary_uri()}")
    except Exception as e:
        print(f"# uis of {uri}: {e!r}", file=sys.stderr)
print("# plugins per kind:", counts, file=sys.stderr)
print("# other param: designations on input control ports:", dict(sorted(other.items())), file=sys.stderr)
