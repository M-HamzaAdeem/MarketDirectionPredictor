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


def test_cors_origins_parses_a_plain_csv_string_from_a_real_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: without Annotated[..., NoDecode] on the list-typed fields,
    # pydantic-settings tries to JSON-decode any env var feeding a list
    # field before _split_csv's mode="before" validator ever runs, so a
    # plain CSV value (the documented, intended format -- see
    # backend/.env.example) raised SettingsError instead of being split.
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost"]
