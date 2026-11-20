"""The ALSA mixer's EQ frequency labels: its geomspace() (no numpy import at start) gives numpy's values
(to rounding: numpy versions differ in the last bit, e.g. 1.834457888680854 vs 1.8344578886808538)."""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("start, stop, num", [(1.7, 18, 32), (32, 18000, 64), (32, 16000, 32), (2, 8, 1), (1, 1000, 4)])
def test_geomspace_matches_numpy(start, stop, num):
    np = pytest.importorskip("numpy")
    from zyngine.zynthian_engine_alsa_mixer import geomspace
    expected = [float(v) for v in np.geomspace(start, stop, num=num)]
    result = geomspace(start, stop, num)
    assert len(result) == len(expected)
    assert result == pytest.approx(expected, rel=1e-12)
