from src.schemas.selt import SELTOX_COLUMNS, SeltRecord, blank_record


def test_selt_schema_columns():
    assert "np" in SELTOX_COLUMNS
    assert "mic_np_µg_ml" in SELTOX_COLUMNS
    assert len(SELTOX_COLUMNS) == 23


def test_blank_record_validates():
    record = SeltRecord(**blank_record())
    assert record.model_dump()["np"] == "NOT_DETECTED"

