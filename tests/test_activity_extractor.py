from src.agents.activity_extractor import ActivityExtractorAgent
from src.agents.base import LLMNotConfigured


class DisabledLLM:
    def complete_text(self, *args, **kwargs):
        raise LLMNotConfigured("disabled")


def test_activity_extractor_deterministic_fallback():
    evidence = [
        {
            "id": "chunk-1",
            "page": 3,
            "source_type": "text",
            "text": "AgNPs showed MIC of 12.5 µg/mL against E. coli ATCC 25922 after 24 h incubation.",
        },
        {
            "id": "chunk-2",
            "page": 4,
            "source_type": "table",
            "text": "Zone of inhibition (ZOI) was 15 mm for Staphylococcus aureus.",
        },
    ]

    rows = ActivityExtractorAgent(llm=DisabledLLM()).extract(evidence)

    assert len(rows) == 2
    assert {row["bacteria"] for row in rows} == {"Escherichia coli", "Staphylococcus aureus"}
    assert all(row["np"] == "Ag" for row in rows)
    assert all(row["mic_np_µg_ml"] == "12.5" for row in rows)
    assert all(row["zoi_np_mm"] == "15" for row in rows)
    assert all(row["time_set_hours"] == "24" for row in rows)
