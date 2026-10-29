import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")
