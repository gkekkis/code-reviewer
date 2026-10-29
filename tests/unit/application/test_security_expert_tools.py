from src.application.agents.security_expert.tools import check_dependency, detect_exposed_secrets

DIFF = (
    "diff --git a/app/services/fx.py b/app/services/fx.py\n"
    "--- a/app/services/fx.py\n"
    "+++ b/app/services/fx.py\n"
    "@@ -1,3 +1,4 @@\n"
    ' TIMEOUT = "30"\n'
    '-FX_API_KEY = "fxk_old_000000"\n'  # gitleaks:allow
    '+FX_API_KEY = "fxk_live_123456"\n'  # gitleaks:allow
    '+DB_PASSWORD = "hunter22"\n'  # gitleaks:allow
    "+RATE = 1.1\n"
    "diff --git a/app/config.py b/app/config.py\n"
    "--- a/app/config.py\n"
    "+++ b/app/config.py\n"
    "@@ -1,1 +1,2 @@\n"
    '+AUTH_TOKEN = "tok_abcdef"\n'  # gitleaks:allow
)


def test_detect_exposed_secrets_finds_added_secrets_in_the_file():
    secrets = detect_exposed_secrets(file_path="app/services/fx.py", diff=DIFF)

    assert secrets == ['FX_API_KEY = "fxk_live_123456"', 'DB_PASSWORD = "hunter22"']  # gitleaks:allow


def test_detect_exposed_secrets_ignores_removed_and_context_lines():
    secrets = detect_exposed_secrets(file_path="app/services/fx.py", diff=DIFF)

    assert 'FX_API_KEY = "fxk_old_000000"' not in secrets  # gitleaks:allow
    assert 'TIMEOUT = "30"' not in secrets


def test_detect_exposed_secrets_only_looks_at_the_requested_file():
    secrets = detect_exposed_secrets(file_path="app/config.py", diff=DIFF)

    assert secrets == ['AUTH_TOKEN = "tok_abcdef"']  # gitleaks:allow


def test_detect_exposed_secrets_file_not_in_diff():
    assert detect_exposed_secrets(file_path="app/other.py", diff=DIFF) == []


def test_detect_exposed_secrets_ignores_values_shorter_than_four_characters():
    diff = 'diff --git a/a.py b/a.py\n+++ b/a.py\n+PASSWORD = "abc"\n'  # gitleaks:allow

    assert detect_exposed_secrets(file_path="a.py", diff=diff) == []


def test_check_dependency_known_vulnerability():
    assert check_dependency(package="requests", version="2.19.1") == "VULNERABLE: requests==2.19.1 (CVE-2018-18074)"


def test_check_dependency_normalizes_package_name():
    assert check_dependency(package="Django", version="3.2.0") == "VULNERABLE: django==3.2.0 (CVE-2021-35042)"


def test_check_dependency_safe_version():
    assert (
        check_dependency(package="requests", version="2.32.0")
        == "No known vulnerability in local database for requests==2.32.0"
    )


def test_check_dependency_unknown_package():
    assert (
        check_dependency(package="flask", version="3.0.0")
        == "No known vulnerability in local database for flask==3.0.0"
    )
