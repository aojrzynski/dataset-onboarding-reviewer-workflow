from dataset_onboarding_reviewer_workflow import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
