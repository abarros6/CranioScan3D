"""Tests for cranial index computation with known landmark coordinates."""

from __future__ import annotations

import numpy as np
import pytest

from cranioscan.measurement.cranial_indices import (
    all_measurements,
    ap_length,
    bitemporal_width,
    cephalic_index,
    cranial_vault_asymmetry_index,
)


def test_cephalic_index_normal_range():
    """CI should return correct value for known inputs."""
    ci = cephalic_index(bitemporal_width=140.0, ap_length=175.0)
    assert abs(ci - 80.0) < 0.001


def test_cephalic_index_dolichocephalic():
    """CI below 75 should be returned correctly (dolichocephaly range)."""
    ci = cephalic_index(bitemporal_width=120.0, ap_length=175.0)
    assert ci < 75.0


def test_cephalic_index_brachycephalic():
    """CI above 85 should be returned correctly (brachycephaly range)."""
    ci = cephalic_index(bitemporal_width=160.0, ap_length=175.0)
    assert ci > 85.0


def test_cephalic_index_zero_ap_raises():
    """CI should raise ValueError if ap_length is zero."""
    with pytest.raises(ValueError):
        cephalic_index(bitemporal_width=140.0, ap_length=0.0)


def test_cephalic_index_negative_ap_raises():
    """CI should raise ValueError if ap_length is negative."""
    with pytest.raises(ValueError):
        cephalic_index(bitemporal_width=140.0, ap_length=-10.0)


def test_cvai_symmetric_skull():
    """CVAI should be 0 for a perfectly symmetric skull."""
    cvai = cranial_vault_asymmetry_index(diagonal_1=180.0, diagonal_2=180.0)
    assert cvai == pytest.approx(0.0)


def test_cvai_asymmetric_skull():
    """CVAI should reflect asymmetry correctly."""
    cvai = cranial_vault_asymmetry_index(diagonal_1=180.0, diagonal_2=172.0)
    expected = (8.0 / 180.0) * 100.0
    assert cvai == pytest.approx(expected, rel=1e-5)


def test_cvai_order_independent():
    """CVAI should give same result regardless of diagonal order."""
    cvai1 = cranial_vault_asymmetry_index(180.0, 172.0)
    cvai2 = cranial_vault_asymmetry_index(172.0, 180.0)
    assert cvai1 == pytest.approx(cvai2)


def test_cvai_zero_diagonal_raises():
    """CVAI should raise ValueError if diagonal_1 is zero."""
    with pytest.raises(ValueError):
        cranial_vault_asymmetry_index(diagonal_1=0.0, diagonal_2=180.0)


def test_cvai_non_negative():
    """CVAI should always be >= 0."""
    for d1, d2 in [(180.0, 172.0), (172.0, 180.0), (150.0, 150.0)]:
        cvai = cranial_vault_asymmetry_index(d1, d2)
        assert cvai >= 0.0


def test_ap_length_aligned(head_landmarks):
    """AP length should equal Euclidean distance between glabella and opisthocranion."""
    length = ap_length(head_landmarks["glabella"], head_landmarks["opisthocranion"])
    expected = np.linalg.norm(head_landmarks["opisthocranion"] - head_landmarks["glabella"])
    assert length == pytest.approx(expected)


def test_ap_length_3d_diagonal():
    """AP length should work for diagonal 3D vectors."""
    g = np.array([1.0, 2.0, 3.0])
    o = np.array([4.0, 6.0, 3.0])
    length = ap_length(g, o)
    assert length == pytest.approx(5.0)


def test_bitemporal_width_aligned(head_landmarks):
    """Bitemporal width should equal Euclidean distance between eurion landmarks."""
    width = bitemporal_width(head_landmarks["eurion_l"], head_landmarks["eurion_r"])
    expected = np.linalg.norm(head_landmarks["eurion_r"] - head_landmarks["eurion_l"])
    assert width == pytest.approx(expected)


def test_bitemporal_width_symmetric():
    """Symmetric eurions should give positive width."""
    el = np.array([65.0, -68.0, 10.0])
    er = np.array([65.0, 68.0, 10.0])
    width = bitemporal_width(el, er)
    assert width == pytest.approx(136.0)


def test_all_measurements_returns_expected_keys(head_landmarks):
    """all_measurements should return a dict with required keys."""
    result = all_measurements(
        glabella=head_landmarks["glabella"],
        opisthocranion=head_landmarks["opisthocranion"],
        eurion_l=head_landmarks["eurion_l"],
        eurion_r=head_landmarks["eurion_r"],
    )
    assert "ap_length_mm" in result
    assert "bitemporal_width_mm" in result
    assert "cephalic_index" in result


def test_all_measurements_no_cvai_without_diagonals(head_landmarks):
    """all_measurements should not include CVAI when diagonals are not provided."""
    result = all_measurements(
        glabella=head_landmarks["glabella"],
        opisthocranion=head_landmarks["opisthocranion"],
        eurion_l=head_landmarks["eurion_l"],
        eurion_r=head_landmarks["eurion_r"],
    )
    assert "cvai" not in result


def test_all_measurements_with_cvai(head_landmarks):
    """all_measurements should include CVAI when diagonals are provided."""
    result = all_measurements(
        glabella=head_landmarks["glabella"],
        opisthocranion=head_landmarks["opisthocranion"],
        eurion_l=head_landmarks["eurion_l"],
        eurion_r=head_landmarks["eurion_r"],
        diagonal_1=180.0,
        diagonal_2=175.0,
    )
    assert "cvai" in result
    assert result["cvai"] >= 0.0


def test_all_measurements_values_consistent(head_landmarks):
    """Measurements returned by all_measurements should be self-consistent."""
    result = all_measurements(
        glabella=head_landmarks["glabella"],
        opisthocranion=head_landmarks["opisthocranion"],
        eurion_l=head_landmarks["eurion_l"],
        eurion_r=head_landmarks["eurion_r"],
    )
    ci_check = (result["bitemporal_width_mm"] / result["ap_length_mm"]) * 100.0
    assert result["cephalic_index"] == pytest.approx(ci_check)
