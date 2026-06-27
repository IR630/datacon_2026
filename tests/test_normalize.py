from src.postprocess.normalize import normalize_bacteria, normalize_missing, normalize_np, parse_nm_range


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

