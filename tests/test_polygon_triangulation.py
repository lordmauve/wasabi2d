"""Fill-index integration without requiring a graphics context."""
from array import array

import numpy as np
import pytest

from wasabi2d.primitives import polygons


def polygon(vertices):
    result = polygons.Polygon.__new__(polygons.Polygon)
    result.orig_verts = np.ones((len(vertices), 3), dtype='f4')
    result.orig_verts[:, :2] = vertices
    return result


def test_earstrip_conversion_and_lifetime(monkeypatch):
    p = polygon([(0, 0), (2, 0), (0, 2)])
    raw = array('I', [0, 1, 2])

    def triangulate(view):
        assert view.dtype == np.float32
        assert view.strides == (12, 4)
        assert np.shares_memory(view, p.orig_verts)
        return raw

    monkeypatch.setattr(polygons, 'triangulate', triangulate)
    indices = p._fill_indices_earstrip()
    assert indices.dtype == np.uint32
    assert indices.ndim == 1
    assert np.shares_memory(indices, np.asarray(raw))
    del raw
    np.testing.assert_array_equal(indices, [0, 1, 2])


def test_refusal_uses_existing_earcut(monkeypatch):
    p = polygon([(0, 0), (2, 0), (0, 2)])

    def refuse(view):
        raise ValueError('polygon could not be triangulated exactly')

    monkeypatch.setattr(polygons, 'triangulate', refuse)
    np.testing.assert_array_equal(p._fill_indices_earstrip(), p._fill_indices_mapbox_earcut())


def test_installed_earstrip_selected():
    if polygons.triangulate is None:
        pytest.skip('install wasabi-geom Earstrip feature wheel for integration')
    assert polygons.Polygon._fill_indices is polygons.Polygon._fill_indices_earstrip
    p = polygon([(0, 0), (4, 0), (4, 4), (2, 1), (0, 4)])
    indices = p._fill_indices()
    assert indices.dtype == np.uint32 and indices.ndim == 1
    points = p.orig_verts[:, :2].astype('f8')[indices.reshape(-1, 3)]
    a, b = points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]
    areas = (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) / 2
    assert np.all(areas >= 0)
    assert areas.sum() == pytest.approx(10)


def test_real_non_simple_polygon_retains_earcut_result():
    if polygons.triangulate is None:
        pytest.skip('install wasabi-geom Earstrip feature wheel for integration')
    p = polygon([(0, 0), (2, 2), (0, 2), (2, 0)])
    with pytest.raises(ValueError):
        polygons.triangulate(p.orig_verts[:, :2])
    np.testing.assert_array_equal(p._fill_indices(), p._fill_indices_mapbox_earcut())
