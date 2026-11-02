import jj_eval.__main__ as cli


def test_run_reports_a_harbor_failure_instead_of_crashing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "HARBOR", ["false"])  # exits 1 without writing a job

    status = cli.main(["run", "--jj-version", "0.46.0", "--scenario", "create-bookmark", "--work-dir", str(tmp_path)])

    assert status == 1
    assert "harbor wrote no results" in capsys.readouterr().err
