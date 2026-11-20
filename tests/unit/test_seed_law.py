from conftest import SPEC

from ramp import config


def test_seed_copies_both_law_files_when_missing(tmp_path):
    home = tmp_path / "h"
    assert config.seed_law(home) == ["descriptors.yaml", "claims.yaml"]
    for name in config.LAW_FILES:
        assert (home / name).read_bytes() == (SPEC / name).read_bytes()


def test_seed_never_overwrites_an_existing_file(tmp_path):
    (tmp_path / "claims.yaml").write_text("java: 5\n")
    assert config.seed_law(tmp_path) == ["descriptors.yaml"]
    assert (tmp_path / "claims.yaml").read_text() == "java: 5\n"
    assert config.seed_law(tmp_path) == []


def test_bundled_copy_is_the_repo_law():
    for name in config.LAW_FILES:
        assert config.bundled_law(name).read_bytes() == (SPEC / name).read_bytes()
