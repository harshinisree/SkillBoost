def test_init_db_command_creates_tables(app):
    result = app.test_cli_runner().invoke(args=["init-db"])

    assert result.exit_code == 0
    assert "Tables created" in result.output
