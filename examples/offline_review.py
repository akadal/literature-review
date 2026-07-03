"""Build a grounded review from in-memory example records."""

from literature_reviewer import LiteratureReviewer, ReviewRequest

request = ReviewRequest(
    topic="blockchain tourism",
    year_range="2020-2026",
    fetch_abstracts=False,
    output_dir="output/example_offline",
)

wos_records = [
    {
        "UID": "WOS:0001",
        "Title": "Blockchain adoption in tourism platforms",
        "Year": 2024,
        "DOI": "10.1000/example",
        "Times_Cited": 12,
        "Journal": "Tourism Systems",
    }
]

scopus_records = [
    {
        "EID": "2-s2.0-0001",
        "Title": "Blockchain adoption in tourism platforms",
        "Year": 2024,
        "DOI": "https://doi.org/10.1000/example",
        "CitedBy_Count": 11,
        "Journal": "Tourism Systems",
    }
]

result = LiteratureReviewer().from_records(request, wos_records=wos_records, scopus_records=scopus_records)
print(result.output_paths["review_markdown"])
