import pytest
from git_repo_jumper.cli.column_widths import ColumnConfig, ColumnWidthsAdjuster


def make_adjuster(available_width: int) -> ColumnWidthsAdjuster:
    """Helper: 4-column config with total min_width of 26."""
    config = {
        'name': ColumnConfig(
            min_width=10, max_width=40, stretch_priority=1, shrink_priority=4
        ),
        'branch': ColumnConfig(
            min_width=5, max_width=20, stretch_priority=1, shrink_priority=2
        ),
        'status': ColumnConfig(
            min_width=6, max_width=10, stretch_priority=1, shrink_priority=3
        ),
        'github': ColumnConfig(
            min_width=5, max_width=30, stretch_priority=1, shrink_priority=1
        ),
    }
    return ColumnWidthsAdjuster(column_config=config, available_width=available_width)


class TestColumnWidthsAdjuster:
    def test_negative_available_width_raises_value_error(self):
        with pytest.raises(ValueError):
            make_adjuster(-1)

    def test_column_names_written_to_config(self):
        adjuster = make_adjuster(50)
        for name, config in adjuster._column_config.items():
            assert config.name == name

    def test_exact_fit_returns_min_widths(self):
        # total min = 10 + 5 + 6 + 5 = 26
        adjuster = make_adjuster(26)
        widths = adjuster.get_calculated_widths()
        assert widths == {'name': 10, 'branch': 5, 'status': 6, 'github': 5}

    def test_stretch_grows_columns_beyond_min(self):
        adjuster = make_adjuster(50)
        widths = adjuster.get_calculated_widths()
        assert widths['name'] > 10
        assert widths['branch'] > 5

    def test_stretch_total_equals_available_width(self):
        adjuster = make_adjuster(50)
        widths = adjuster.get_calculated_widths()
        assert sum(widths.values()) == 50

    def test_stretch_does_not_exceed_max_width(self):
        adjuster = make_adjuster(200)
        widths = adjuster.get_calculated_widths()
        assert widths['name'] <= 40
        assert widths['branch'] <= 20
        assert widths['status'] <= 10
        assert widths['github'] <= 30

    def test_shrink_reduces_total_to_available(self):
        adjuster = make_adjuster(15)
        widths = adjuster.get_calculated_widths()
        assert sum(widths.values()) <= 15

    def test_shrink_never_goes_below_zero(self):
        adjuster = make_adjuster(0)
        widths = adjuster.get_calculated_widths()
        for w in widths.values():
            assert w >= 0

    def test_shrink_priority_one_shrinks_first(self):
        # github has shrink_priority=1 → shrinks first.
        # deficit = 26 - 21 = 5, github min = 5 → github absorbs all → width=0
        adjuster = make_adjuster(21)
        widths = adjuster.get_calculated_widths()
        assert widths['github'] == 0
        assert widths['name'] == 10   # lowest shrink priority, untouched
