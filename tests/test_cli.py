import json

from halls_of_knowledge import cli
from halls_of_knowledge.cli import main


def test_nomination_discovery_command_writes_repeatable_schema(tmp_path):
    output = tmp_path / "discovery.json"

    status = main(
        [
            "corpus",
            "discover",
            "--nominate",
            "Gandalf",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    document = json.loads(output.read_text())
    assert document["schema_version"] == 1
    assert document["records"][0]["observed_page_title"] == "Gandalf"
    assert document["records"][0]["discovery_route"] == "human nomination"


def test_category_discovery_loads_contact_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HOK_WIKIMEDIA_CONTACT", raising=False)
    (tmp_path / ".env").write_text("HOK_WIKIMEDIA_CONTACT=mailto:operator@example.test\n")
    observed = {}

    class Catalog:
        def __init__(self, *, contact, minimum_request_interval):
            observed["contact"] = contact

        def articles(self, category, limit):
            return ()

    monkeypatch.setattr(cli, "PywikibotCatalog", Catalog)

    status = main(
        [
            "corpus",
            "discover",
            "--category",
            "Category:Middle-earth",
            "--output",
            str(tmp_path / "discovery.json"),
        ]
    )

    assert status == 0
    assert observed["contact"] == "mailto:operator@example.test"
