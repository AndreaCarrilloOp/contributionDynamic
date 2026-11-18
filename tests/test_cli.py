import pytest

from contribution_dynamic import __version__, cli


def test_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["contribution_dynamic", "--version"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_batch_cli(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", [
        "contribution_dynamic", "batch", "--scenario", "chess",
        "--theme", "both", "--output-dir", str(tmp_path),
    ])
    assert cli.main() == 0
    assert {p.name for p in tmp_path.glob("*.svg")} == {
        "chess-dark.svg", "chess-light.svg",
    }
