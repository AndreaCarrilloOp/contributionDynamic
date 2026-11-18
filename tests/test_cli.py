import pytest

from contribution_dynamic import __version__, cli


def test_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["contribution_dynamic", "--version"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == __version__
