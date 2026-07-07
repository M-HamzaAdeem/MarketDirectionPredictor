import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_mock_time_acceleration_defaults_to_60x() -> None:
    settings = Settings(_env_file=None)
    assert settings.mock_time_acceleration == 60.0


@pytest.mark.parametrize("value", [0, -1, -60.0])
def test_mock_time_acceleration_rejects_non_positive_values(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mock_time_acceleration=value)
