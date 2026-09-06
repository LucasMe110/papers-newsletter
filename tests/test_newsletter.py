"""Testes de sanitização de credenciais lidas do ambiente."""
import os
import pytest

from newsletter import clean_env, resolve_smtp_user, resolve_recipients


@pytest.fixture(autouse=True)
def _clean_environ(monkeypatch):
    for key in ("EMAIL_FROM", "GMAIL_APP_PASSWORD", "EMAIL_RECIPIENTS"):
        monkeypatch.delenv(key, raising=False)


class TestCleanEnv:
    def test_removes_surrounding_whitespace(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "  user@gmail.com  ")
        assert clean_env("EMAIL_FROM") == "user@gmail.com"

    def test_removes_double_quotes(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", '"user@gmail.com"')
        assert clean_env("EMAIL_FROM") == "user@gmail.com"

    def test_removes_single_quotes(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "'user@gmail.com'")
        assert clean_env("EMAIL_FROM") == "user@gmail.com"

    def test_removes_quotes_around_whitespace(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", '  " user@gmail.com "  ')
        assert clean_env("EMAIL_FROM") == "user@gmail.com"

    def test_raises_when_variable_is_missing(self):
        with pytest.raises(KeyError):
            clean_env("EMAIL_FROM")

    def test_raises_when_variable_is_empty_after_cleaning(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", '  ""  ')
        with pytest.raises(ValueError):
            clean_env("EMAIL_FROM")


class TestResolveSmtpUser:
    def test_returns_bare_address_unchanged(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "user@gmail.com")
        assert resolve_smtp_user() == ("user@gmail.com", "user@gmail.com")

    def test_extracts_address_from_display_name_format(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "Papers Newsletter <user@gmail.com>")
        login, header = resolve_smtp_user()
        assert login == "user@gmail.com"
        assert header == "Papers Newsletter <user@gmail.com>"

    def test_extracts_address_from_quoted_display_name_format(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", '"Papers <user@gmail.com>"')
        assert resolve_smtp_user()[0] == "user@gmail.com"

    def test_rejects_value_without_address(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "Papers Newsletter")
        with pytest.raises(ValueError):
            resolve_smtp_user()


class TestResolveRecipients:
    def test_splits_and_strips_multiple_recipients(self, monkeypatch):
        monkeypatch.setenv("EMAIL_RECIPIENTS", " a@x.com , b@y.com ")
        assert resolve_recipients() == ["a@x.com", "b@y.com"]

    def test_removes_quotes_around_the_whole_list(self, monkeypatch):
        monkeypatch.setenv("EMAIL_RECIPIENTS", '"a@x.com,b@y.com"')
        assert resolve_recipients() == ["a@x.com", "b@y.com"]

    def test_ignores_empty_entries_from_trailing_comma(self, monkeypatch):
        monkeypatch.setenv("EMAIL_RECIPIENTS", "a@x.com,,b@y.com,")
        assert resolve_recipients() == ["a@x.com", "b@y.com"]

    def test_raises_when_no_valid_recipient_remains(self, monkeypatch):
        monkeypatch.setenv("EMAIL_RECIPIENTS", " , , ")
        with pytest.raises(ValueError):
            resolve_recipients()
