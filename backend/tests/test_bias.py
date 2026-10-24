import numpy as np
import pandas as pd

from app.config import PST
from app.validation.bias import apply_bias, fit_bias_table
from tests.helpers import stub


@stub
def test_constant_offset_recovered_and_applied():
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz=PST)
    rng = np.random.default_rng(1)
    observed = pd.Series(
        50 + 15 * np.sin(np.arange(len(idx)) * 2 * np.pi / 24) + rng.normal(0, 2, len(idx)), index=idx
    )
    gridded = observed - 2.0
    table = fit_bias_table(gridded, observed)
    assert table.shape == (12, 24)
    assert np.allclose(table.values, 2.0)
    assert np.allclose(apply_bias(gridded, table).values, observed.values)
