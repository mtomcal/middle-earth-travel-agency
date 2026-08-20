import hashlib

import pytest

from middle_earth_travel_agency.experiment_config import load_experiment_config


BASELINE = """\
schema_version: 1
index:
  tokenizer: unicode61
  remove_diacritics: 2
retrieval:
  query_mode: all-terms
  result_limit: 5
  title_weight: 5.0
  heading_weight: 2.0
  body_weight: 1.0
  tie_breaker: passage-id
agent:
  retrieval_budget: 4
  temperature: 0.0
  max_output_tokens: 1024
provider:
  request_timeout_seconds: 60
  attempt_timeout_seconds: 300
  max_retries: 1
runner:
  max_concurrency: 5
report:
  evidence_excerpt_characters: 1200
"""


def _config_file(tmp_path, content=BASELINE):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "experiment.yaml"
    path.write_text(content)
    return path


def test_loads_the_complete_baseline_into_immutable_normalized_values(tmp_path):
    config = load_experiment_config(_config_file(tmp_path))

    assert config.index.tokenizer == "unicode61"
    assert config.index.remove_diacritics == 2
    assert config.retrieval.result_limit == 5
    assert config.retrieval.weights == (5.0, 2.0, 1.0)
    assert config.agent.retrieval_budget == 4
    assert config.provider.request_timeout_seconds == 60.0
    assert config.runner.max_concurrency == 5
    assert config.report.evidence_excerpt_characters == 1200
    with pytest.raises(AttributeError):
        setattr(config.agent, "retrieval_budget", 1)


def test_canonical_non_secret_representation_and_identity_are_stable(tmp_path):
    config = load_experiment_config(_config_file(tmp_path))
    reordered = BASELINE.replace("schema_version: 1\n", "").replace(
        "report:\n  evidence_excerpt_characters: 1200\n",
        "report:\n  evidence_excerpt_characters: 1200\nschema_version: 1\n",
    )

    assert (
        load_experiment_config(_config_file(tmp_path / "second", reordered)).to_dict()
        == config.to_dict()
    )
    assert load_experiment_config(_config_file(tmp_path / "second", reordered)).config_identity == (
        config.config_identity
    )
    assert config.config_identity == hashlib.sha256(config.canonical_json().encode()).hexdigest()
    assert "secret" not in config.canonical_json()


def test_index_identity_changes_only_for_index_and_retrieval_settings(tmp_path):
    baseline = load_experiment_config(_config_file(tmp_path))
    runner_change = load_experiment_config(
        _config_file(
            tmp_path / "runner", BASELINE.replace("max_concurrency: 5", "max_concurrency: 4")
        )
    )
    retrieval_change = load_experiment_config(
        _config_file(tmp_path / "retrieval", BASELINE.replace("result_limit: 5", "result_limit: 6"))
    )

    assert runner_change.config_identity != baseline.config_identity
    assert runner_change.index_identity == baseline.index_identity
    assert retrieval_change.config_identity != baseline.config_identity
    assert retrieval_change.index_identity != baseline.index_identity


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (BASELINE.replace("schema_version: 1", "schema_version: 2"), "schema_version"),
        (BASELINE.replace("schema_version: 1", "schema_version: 1\nunknown: value"), "unknown"),
        (BASELINE.replace("result_limit: 5", "result_limit: 5\n  result_limit: 3"), "duplicate"),
        (BASELINE.replace("query_mode: all-terms", "query_mode: !unsafe all-terms"), "tag"),
        (BASELINE.replace("result_limit: 5", "result_limit: 51"), "result_limit"),
        (
            BASELINE.replace("title_weight: 5.0", "title_weight: 0")
            .replace("heading_weight: 2.0", "heading_weight: 0")
            .replace("body_weight: 1.0", "body_weight: 0"),
            "weight",
        ),
        (
            BASELINE.replace("attempt_timeout_seconds: 300", "attempt_timeout_seconds: 59"),
            "attempt_timeout",
        ),
        (BASELINE.replace("temperature: 0.0", "temperature: true"), "temperature"),
    ],
)
def test_rejects_unsafe_or_invalid_configuration(tmp_path, content, message):
    with pytest.raises(ValueError, match=message):
        load_experiment_config(_config_file(tmp_path, content))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("tokenizer: unicode61", "tokenizer: invalid", "tokenizer"),
        ("remove_diacritics: 2", "remove_diacritics: -1", "remove_diacritics"),
        ("remove_diacritics: 2", "remove_diacritics: 3", "remove_diacritics"),
        ("query_mode: all-terms", "query_mode: invalid", "query_mode"),
        ("result_limit: 5", "result_limit: 0", "result_limit"),
        ("result_limit: 5", "result_limit: 51", "result_limit"),
        ("title_weight: 5.0", "title_weight: -1", "title_weight"),
        ("title_weight: 5.0", "title_weight: 101", "title_weight"),
        ("heading_weight: 2.0", "heading_weight: -1", "heading_weight"),
        ("heading_weight: 2.0", "heading_weight: 101", "heading_weight"),
        ("body_weight: 1.0", "body_weight: -1", "body_weight"),
        ("body_weight: 1.0", "body_weight: 101", "body_weight"),
        ("tie_breaker: passage-id", "tie_breaker: invalid", "tie_breaker"),
        ("retrieval_budget: 4", "retrieval_budget: 0", "retrieval_budget"),
        ("retrieval_budget: 4", "retrieval_budget: 21", "retrieval_budget"),
        ("temperature: 0.0", "temperature: -0.1", "temperature"),
        ("temperature: 0.0", "temperature: 2.1", "temperature"),
        ("max_output_tokens: 1024", "max_output_tokens: 63", "max_output_tokens"),
        ("max_output_tokens: 1024", "max_output_tokens: 8193", "max_output_tokens"),
        (
            "request_timeout_seconds: 60",
            "request_timeout_seconds: 0",
            "request_timeout_seconds",
        ),
        (
            "request_timeout_seconds: 60",
            "request_timeout_seconds: 601",
            "request_timeout_seconds",
        ),
        (
            "attempt_timeout_seconds: 300",
            "attempt_timeout_seconds: 0",
            "attempt_timeout_seconds",
        ),
        (
            "attempt_timeout_seconds: 300",
            "attempt_timeout_seconds: 3601",
            "attempt_timeout_seconds",
        ),
        ("max_retries: 1", "max_retries: -1", "max_retries"),
        ("max_retries: 1", "max_retries: 4", "max_retries"),
        ("max_concurrency: 5", "max_concurrency: 0", "max_concurrency"),
        ("max_concurrency: 5", "max_concurrency: 6", "max_concurrency"),
        (
            "evidence_excerpt_characters: 1200",
            "evidence_excerpt_characters: 199",
            "evidence_excerpt_characters",
        ),
        (
            "evidence_excerpt_characters: 1200",
            "evidence_excerpt_characters: 4001",
            "evidence_excerpt_characters",
        ),
    ],
)
def test_rejects_every_documented_out_of_range_value(tmp_path, old, new, message):
    with pytest.raises(ValueError, match=message):
        load_experiment_config(_config_file(tmp_path, BASELINE.replace(old, new)))


@pytest.mark.parametrize(
    "content",
    [
        BASELINE.replace("report:\n  evidence_excerpt_characters: 1200\n", ""),
        BASELINE.replace("result_limit: 5", "result_limit: 5\n  unknown: true"),
        BASELINE.replace("max_output_tokens: 1024", "max_output_tokens: words"),
        BASELINE.replace("index:\n  tokenizer: unicode61\n  remove_diacritics: 2", "index: []"),
        BASELINE.replace("index:", "defaults: &defaults {}\nindex:\n  <<: *defaults"),
    ],
)
def test_rejects_missing_unknown_malformed_and_merged_values(tmp_path, content):
    with pytest.raises(ValueError):
        load_experiment_config(_config_file(tmp_path, content))
