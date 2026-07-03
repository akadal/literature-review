from literature_reviewer.cli import main


def test_doctor_does_not_require_live_apis(capsys) -> None:
    code = main(["doctor"])
    captured = capsys.readouterr()

    assert code == 0
    assert "WOS_API_KEY:" in captured.out
    assert "SCOPUS_API_KEY:" in captured.out
    assert "Example WoS query:" in captured.out
