from scripts import verify_branch_protection


def test_missing_token_skips_verification(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    assert verify_branch_protection.main([]) == 0
    captured = capsys.readouterr()
    assert "skipping branch protection" in captured.err
