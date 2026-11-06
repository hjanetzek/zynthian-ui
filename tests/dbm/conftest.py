# -*- coding: utf-8 -*-
"""pytest doesn't collect the DrivenByMoss drivers' tests: they replace zyngine with stand-ins
(zynstubs.py) and need DrivenByMoss. They have their own runner: ``./run_tests.sh dbm``
(``tests/dbm/run_tests.py``)."""

collect_ignore_glob = ["*.py"]
