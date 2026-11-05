from viralpanel.config import Settings, get_settings


def test_settings_defaults():
    s = Settings()
    assert s.timezone == "America/Sao_Paulo"
    assert s.database_url.startswith("postgresql+psycopg2://")


def test_engine_creation():
    from viralpanel.database import SessionLocal, engine

    assert engine is not None
    assert SessionLocal is not None
    assert get_settings() is get_settings()
