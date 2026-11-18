"""The ALSA mixer's EQ frequency labels: its geomspace() (no numpy import at start) gives numpy's values."""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("start, stop, num", [(1.7, 18, 32), (32, 18000, 64), (32, 16000, 32), (2, 8, 1), (1, 1000, 4)])
def test_geomspace_matches_numpy(start, stop, num):
    np = pytest.importorskip("numpy")
    from zyngine.zynthian_engine_alsa_mixer import geomspace
    assert geomspace(start, stop, num) == [float(v) for v in np.geomspace(start, stop, num=num)]
