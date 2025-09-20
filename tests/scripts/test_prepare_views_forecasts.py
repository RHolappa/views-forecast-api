import numpy as np
import pandas as pd
import pytest

from scripts.prepare_views_forecasts import (
    FORECAST_COLUMNS,
    prepare_forecast_dataframe,
)


@pytest.fixture()
def sample_pred_paths(tmp_path):
    preds_path = tmp_path / "preds.parquet"
    hdi_path = tmp_path / "hdi.parquet"

    draws_one = np.array([0.0, 1.0, 2.0, 12.0], dtype=np.float32)
    draws_two = np.array([5.0, 8.0, 13.0, 21.0], dtype=np.float32)

    pred_df = pd.DataFrame(
        {
            "pred_ln_sb_best": [
                np.log1p(draws_one).astype(np.float32),
                np.log1p(draws_two).astype(np.float32),
            ],
            "country_id": [7, 840],
            "lat": [1.5, -2.5],
            "lon": [34.5, 40.1],
        },
        index=pd.MultiIndex.from_tuples(
            [(409, 1001), (410, 1002)], names=["month_id", "priogrid_id"]
        ),
    )
    pred_df.to_parquet(preds_path)

    lower_one, upper_one = np.quantile(draws_one, [0.05, 0.95])
    lower_two, upper_two = np.quantile(draws_two, [0.05, 0.95])

    hdi_df = pd.DataFrame(
        {
            "pred_ln_sb_best_hdi_lower": [
                np.log1p(lower_one).astype(np.float32),
                np.log1p(lower_two).astype(np.float32),
            ],
            "pred_ln_sb_best_hdi_upper": [
                np.log1p(upper_one).astype(np.float32),
                np.log1p(upper_two).astype(np.float32),
            ],
        },
        index=pd.MultiIndex.from_tuples(
            [(409, 1001), (410, 1002)], names=["month_id", "priogrid_id"]
        ),
    )
    hdi_df.to_parquet(hdi_path)

    return preds_path, hdi_path, draws_one, draws_two, lower_one, upper_one, lower_two, upper_two


def test_prepare_forecast_dataframe(sample_pred_paths):
    (
        preds_path,
        hdi_path,
        draws_one,
        draws_two,
        lower_one,
        upper_one,
        lower_two,
        upper_two,
    ) = sample_pred_paths

    result = prepare_forecast_dataframe(preds_path, hdi_path)

    assert list(result.columns) == FORECAST_COLUMNS
    assert result.shape == (2, len(FORECAST_COLUMNS))
    assert result["month"].tolist() == ["2024-01", "2024-02"]
    assert result["country_id"].tolist() == ["007", "840"]

    float_cols = [
        "latitude",
        "longitude",
        "map",
        "ci_50_low",
        "ci_50_high",
        "ci_90_low",
        "ci_90_high",
        "ci_99_low",
        "ci_99_high",
        "prob_0",
        "prob_1",
        "prob_10",
        "prob_100",
        "prob_1000",
        "prob_10000",
    ]
    for col in float_cols:
        assert result[col].dtype == np.float32

    np.testing.assert_allclose(result.loc[0, "map"], draws_one.mean(), rtol=1e-6)
    np.testing.assert_allclose(result.loc[1, "map"], draws_two.mean(), rtol=1e-6)
    np.testing.assert_allclose(result.loc[0, "prob_10"], 0.25, rtol=1e-6)
    np.testing.assert_allclose(result.loc[1, "prob_1"], 1.0, rtol=1e-6)
    np.testing.assert_allclose(result.loc[0, "ci_90_low"], lower_one, rtol=1e-6)
    np.testing.assert_allclose(result.loc[0, "ci_90_high"], upper_one, rtol=1e-6)
    np.testing.assert_allclose(result.loc[1, "ci_90_low"], lower_two, rtol=1e-6)
    np.testing.assert_allclose(result.loc[1, "ci_90_high"], upper_two, rtol=1e-6)
    np.testing.assert_allclose(result["prob_0"], 1.0 - result["prob_1"], rtol=1e-6)
