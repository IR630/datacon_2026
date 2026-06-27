"""SelTox evidence keywords and regex patterns."""

from __future__ import annotations

import re


ACTIVITY_QUERY = (
    "MIC MBC ZOI zone of inhibition antibacterial antimicrobial bacteria strain MDR ATCC "
    "Escherichia coli Staphylococcus aureus Pseudomonas aeruginosa Klebsiella pneumoniae"
)
NANOPARTICLE_QUERY = (
    "AgNP silver nanoparticle ZnO AuNP CuO TiO2 particle size TEM SEM DLS zeta "
    "hydrodynamic diameter shape spherical"
)
SYNTHESIS_QUERY = (
    "green synthesis biological synthesis plant extract precursor AgNO3 silver nitrate "
    "pH temperature stirring duration solvent concentration"
)

REGEX_PATTERNS = {
    "mic": re.compile(r"\bMIC\b|minimum inhibitory concentration", re.IGNORECASE),
    "zoi": re.compile(r"\bZOI\b|zone of inhibition|inhibition zone", re.IGNORECASE),
    "bacteria": re.compile(
        r"\b(?:E\. coli|Escherichia coli|S\. aureus|Staphylococcus aureus|P\. aeruginosa|"
        r"Pseudomonas aeruginosa|K\. pneumoniae|Klebsiella pneumoniae|B\. subtilis|"
        r"Bacillus subtilis|E\. faecalis|Enterococcus faecalis)\b",
        re.IGNORECASE,
    ),
    "np": re.compile(r"\b(?:AgNPs?|Ag NPs?|silver nanoparticles?|ZnO|AuNPs?|CuO|TiO2)\b", re.IGNORECASE),
    "size_nm": re.compile(r"\b\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*nm\b|\b\d+(?:\.\d+)?\s*nm\b", re.IGNORECASE),
    "ph": re.compile(r"\bpH\s*[-=]?\s*\d+(?:\.\d+)?\b", re.IGNORECASE),
    "temperature": re.compile(r"\b\d+(?:\.\d+)?\s*(?:°\s*)?C\b", re.IGNORECASE),
    "time": re.compile(r"\b\d+(?:\.\d+)?\s*(?:h|hr|hrs|hours|min|minutes)\b", re.IGNORECASE),
    "precursor": re.compile(r"\b(?:AgNO3|silver nitrate|Zn\(NO3\)|HAuCl4|CuSO4)\b", re.IGNORECASE),
}

