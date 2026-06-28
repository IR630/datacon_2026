from src.postprocess.normalize import (
    norm_binary,
    norm_float_num,
    norm_int_num,
    norm_method,
    norm_shape,
    normalize_bacteria,
    normalize_missing,
    normalize_np,
    normalize_seltox_record,
    parse_nm_range,
    seltox_prior_record,
)


def test_missing_values():
    assert normalize_missing(None) == "NOT_DETECTED"
    assert normalize_missing("ND") == "NOT_DETECTED"


def test_bacteria_synonyms():
    assert normalize_bacteria("E. coli") == "Escherichia coli"
    assert normalize_bacteria("S. aureus") == "Staphylococcus aureus"


def test_np_synonyms():
    assert normalize_np("AgNPs") == "Ag"
    assert normalize_np("silver nanoparticles") == "Ag"


def test_nm_range():
    assert parse_nm_range("8-41 nm") == ("8", "41", "24.5")
    assert parse_nm_range("20 nm") == ("20", "20", "20")


def test_float_num_matches_float64_gold():
    # float64 gold stores integers as "10.0"; decimals and negatives preserved.
    assert norm_float_num("10") == "10.0"
    assert norm_float_num("12.5") == "12.5"
    assert norm_float_num("-18") == "-18.0"
    for missing in (None, "nan", "NOT_DETECTED", "", "ND"):
        assert norm_float_num(missing) == "nan"


def test_int_num_matches_str_stored_gold():
    # mic_np_µg_ml is str-stored: integer-style, no ".0".
    assert norm_int_num("100") == "100"
    assert norm_int_num("100.0") == "100"
    assert norm_int_num("12.5") == "12.5"
    assert norm_int_num(None) == "nan"


def test_binary_fields_default_zero():
    assert norm_binary("yes") == "1"
    assert norm_binary("1") == "1"
    assert norm_binary("no") == "0"
    assert norm_binary("0") == "0"
    assert norm_binary(None) == "0"  # mdr/coating have 0% missing, ~85-91% zeros


def test_method_and_shape():
    assert norm_method("mic") == "MIC"
    assert norm_method(None) == "NOT_DETECTED"
    assert norm_shape("Spherical") == "spherical"
    assert norm_shape(None) == "NOT_DETECTED"


def test_seltox_record_defaults():
    out = normalize_seltox_record({"np": "AgNPs", "mic_np_µg_ml": "32", "np_size_min_nm": "8"})
    assert out["np"] == "Ag"
    assert out["mic_np_µg_ml"] == "32"
    assert out["np_size_min_nm"] == "8.0"
    assert out["mdr"] == "0" and out["coating"] == "0"  # binary defaults
    assert out["bacteria"] == "NOT_DETECTED"  # absent string field
    assert out["zoi_np_mm"] == "nan"  # absent numeric field


def test_prior_record_majority_defaults():
    prior = seltox_prior_record()
    # majority-class defaults (lock the no-LLM floor, Macro-F1 ~0.136)
    assert prior["np"] == "Ag"
    assert prior["method"] == "MIC"
    assert prior["shape"] == "spherical"
    assert prior["mdr"] == "0" and prior["coating"] == "0"
    assert prior["precursor_of_np"] == "AgNO3"
    # majority-missing fields still abstain
    assert prior["zoi_np_mm"] == "nan"
    assert prior["concentration_of_precursor_mM"] == "nan"
    assert prior["strain"] == "NOT_DETECTED"

