#!/usr/bin/env python3
"""Which of the LV2 plugins zynthian enables by default are installed, and do they load.

Runs on the device (needs py3-lilv), e.g. from the host:

    ssh jeff@kick-duet.local python3 - < nura/tools/lv2-coverage.py
    ssh jeff@kick-duet.local python3 - --missing --load < nura/tools/lv2-coverage.py

--missing   list the missing plugins, grouped by project (URI prefix), with their names
--load      dlopen every LV2 library (catches unresolved symbols), and instantiate the enabled
            plugins that need no host features (plugins that need urid:map, options, ... are
            only loaded; test those with jalv)
--config    engine configuration with zynthian's defaults (default: the installed zynthian-sys
            config.json)

See docs/nura-lv2-plugins.md.
"""

import argparse
import collections
import ctypes
import glob
import json
import os
import re
import sys

import lilv

DEFAULT_CONFIG = "/usr/share/zynthian/zynthian-sys/config/engine_config.json"
# URI prefixes grouped as one project in the --missing list
GROUPS = r"/(FluidPlug_|swh-plugins/|calf.sourceforge.net/plugins/|distrho.sf.net/plugins/|guitarix.sourceforge.net/plugins/).*"


def project(uri):
    m = re.match(r"(https?://[^/]+(?:/[^/#]+){0,2})", uri) or re.match(r"(urn:[^:]+)", uri)
    return re.sub(GROUPS, r"/\1*", m.group(1) if m else uri)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--missing", action="store_true")
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    engines = json.load(open(args.config))
    enabled = {v["URL"]: v.get("NAME", "") for v in engines.values()
               if v.get("ENABLED") and v.get("URL", "").startswith(("http", "urn"))}

    world = lilv.World()
    world.load_all()
    plugins = {str(p.get_uri()): p for p in world.get_all_plugins()}
    have = [u for u in enabled if u in plugins]
    print(f"installed LV2 plugins: {len(plugins)}; enabled by zynthian: {len(enabled)}, "
          f"installed: {len(have)}, missing: {len(enabled) - len(have)}")

    if args.missing:
        groups = collections.defaultdict(list)
        for uri, name in enabled.items():
            if uri not in plugins:
                groups[project(uri)].append(name)
        for key, names in sorted(groups.items(), key=lambda g: (-len(g[1]), g[0])):
            print(f"{len(names):4d} {key}: {', '.join(sorted(names))[:150]}")

    if args.load:
        libs = sorted(glob.glob("/usr/lib/lv2/*.lv2/*.so"))
        bad = 0
        for so in libs:
            try:
                ctypes.CDLL(so, mode=os.RTLD_NOW | os.RTLD_LOCAL)
            except OSError as e:
                bad += 1
                print(f"LOAD FAILED {so}: {e}")
        print(f"libraries: {len(libs)}, failed to load: {bad}")
        ok, failed, needs_features, keep = 0, 0, 0, []
        for uri in have:
            p = plugins[uri]
            if len(p.get_required_features()):
                needs_features += 1
                continue
            inst = lilv.Instance(p, 48000)
            if inst.instance:
                ok += 1
            else:
                failed += 1
                keep.append(inst)   # its __del__ would free a NULL handle
                print(f"INSTANTIATE FAILED {uri}")
        print(f"instantiated: {ok}, failed: {failed}, need host features (not tested): {needs_features}")
        sys.stdout.flush()
        os._exit(0)   # skip freeing the failed instances


if __name__ == "__main__":
    main()
