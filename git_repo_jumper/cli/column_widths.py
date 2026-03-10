from dataclasses import dataclass
from enum import Enum


@dataclass
class ColumnConfig:
    """
    Configuration for a single column.

    Attributes:
    -----------
    min_width : int
        The minimum width of the column.
    max_width : int
        The maximum width of the column.
    stretch_priority : int | None
        The priority for stretching the column when there is extra space.
        Lower values indicate higher priority.
    shrink_priority : int | None
        The priority for shrinking the column when there is a width deficit.
        Lower values indicate higher priority.
    name : str | None
        The name of the column.
    """
    min_width: int
    max_width: int
    stretch_priority: int | None = None
    shrink_priority: int | None = None
    name: str | None = None


class ColumnAdjustmentStrategy(Enum):
    """
    Strategy for adjusting column widths when available width is insufficient
    or excessive.
    """
    SHRINK = 'shrink'
    STRETCH = 'stretch'

class ColumnWidthsAdjuster:
    """
    Calculates column widths for a fixed available width by distributing space
    across columns according to their min/max constraints and stretch/shrink
    priorities.

    Columns are first set to their minimum width. Remaining space is then
    distributed (stretch) or excess is removed (shrink) in priority order, where
    lower priority values are adjusted first. Columns with the same priority
    are adjusted equally, with overflow redistributed among uncapped columns.

    Attributes:
    -----------
    column_config : dict[str, ColumnConfig]
        Configuration for each column, keyed by column name.
    available_width : int
        The total width available for all columns combined.
    _total_min_width : int
        The sum of the minimum widths of all columns.
    _width_budget : int
        The remaining width to distribute (positive) or remove (negative) after
        accounting for minimum widths.
    _calculated_widths : dict[str, int]
        The calculated width for each column after adjustment.
    """
    _column_config: dict[str, ColumnConfig]
    _available_width: int
    _total_min_width: int
    _width_budget: int
    _calculated_widths: dict[str, int] = {}

    @property
    def column_config(self) -> dict[str, ColumnConfig]:
        return self._column_config

    @property
    def available_width(self) -> int:
        return self._available_width

    @available_width.setter
    def available_width(self, value: int):
        """Set the available width for columns, ensuring it's non-negative."""
        if value < 0:
            raise ValueError('Available width cannot be negative.')
        self._available_width = value


    def __init__(
        self, column_config: dict[str, ColumnConfig], available_width: int
    ):
        self._column_config = column_config
        self.available_width = available_width
        self._add_names_to_column_config()


    def get_calculated_widths(self) -> dict[str, int]:
        """
        Calculates and returns the adjusted width for each column.

        Returns
        -------
        dict[str, int]
            Mapping of column names to their calculated widths in characters.
        """
        self._calculated_widths = {}
        self._total_min_width = self._calculate_total_min_width()
        self._width_budget = self.available_width - self._total_min_width

        # List of columns sorted by shrink/stretch priority
        # (lowest value first = highest priority)
        columns_sorted_by_shrink_prio = sorted(
            self.column_config.values(),
            key=lambda col: col.shrink_priority
                if col.shrink_priority is not None else float('inf')
        )

        columns_sorted_by_stretch_prio = sorted(
            self.column_config.values(),
            key=lambda col: col.stretch_priority
                if col.stretch_priority is not None else float('inf')
        )

        # Shrink or stretch columns based on the width budget
        if self._width_budget < 0:
            self._adjust_columns(
                ColumnAdjustmentStrategy.SHRINK, columns_sorted_by_shrink_prio
            )
        elif self._width_budget > 0:
            self._adjust_columns(
                ColumnAdjustmentStrategy.STRETCH, columns_sorted_by_stretch_prio
            )
        else:
            for column_name, config in self.column_config.items():
                self._calculated_widths[column_name] = config.min_width

        return self._calculated_widths


    def _add_names_to_column_config(self):
        """Writes each column's dict key into its ColumnConfig.name field."""
        for name, config in self.column_config.items():
            config.name = name

    def _calculate_total_min_width(self) -> int:
        """Returns the sum of all columns' minimum widths."""
        total_width = 0
        for config in self.column_config.values():
            total_width += config.min_width
        return total_width

    def _adjust_columns(
        self,
        strategy: ColumnAdjustmentStrategy,
        columns_sorted_by_prio: list[ColumnConfig]
    ):
        """
        Iterates over priority groups and distributes the width budget.

        Columns are processed in ascending priority order. Columns sharing
        the same priority are adjusted together. Already-processed columns
        are skipped. The remaining budget is passed on to the next group.

        Parameters
        ----------
        strategy : ColumnAdjustmentStrategy
            Whether to shrink or stretch columns.
        columns_sorted_by_prio : list[ColumnConfig]
            Columns sorted by the relevant priority (ascending).
        """
        calculated_widths = self._calculated_widths

        if strategy == ColumnAdjustmentStrategy.SHRINK:
            do_shrink = True
        else:
            do_shrink = False

        # Loop columns and adjusting widths within each priority group
        for i, column_config in enumerate(columns_sorted_by_prio):
            columns_with_same_prio = [column_config]

            # Get all columns with the same priority (including the current one)
            for next_column_config in columns_sorted_by_prio[i+1:]:
                if do_shrink:
                    has_same_prio = (next_column_config.shrink_priority
                                     == column_config.shrink_priority)
                else:
                    has_same_prio = (next_column_config.stretch_priority
                                     == column_config.stretch_priority)

                if has_same_prio:
                    columns_with_same_prio.append(next_column_config)
                else:
                    break

            # Skip columns already processed as part of a previous priority group
            if column_config.name in calculated_widths:
                continue

            # Initialize widths at min_width for this priority group
            for col in columns_with_same_prio:
                if col.name:
                    calculated_widths[col.name] = col.min_width

            if self._width_budget == 0:
                continue

            self._distribute_budget(columns_with_same_prio, do_shrink)

    def _distribute_budget(
        self, columns_with_same_prio: list[ColumnConfig],do_shrink: bool
    ):
        """
        Distributes the current width budget equally among columns with the same
        priority, respecting each column's max_width (stretch) or a floor
        of 0 (shrink). Space that cannot be applied to a capped column is
        redistributed among the remaining uncapped columns.

        Updates self._width_budget with any undistributed remainder for the
        next priority group.

        Parameters
        ----------
        columns_with_same_prio : list[ColumnConfig]
            Columns in the current priority group, all pre-initialized to
            their min_width in self._calculated_widths.
        do_shrink : bool
            True to shrink columns, False to stretch.
        """
        calculated_widths = self._calculated_widths
        remaining_cols = list(columns_with_same_prio)
        remaining_budget = abs(self._width_budget)

        # Loop until all the budget is distributed or there are no more columns
        while remaining_budget > 0 and remaining_cols:
            per_col = remaining_budget // len(remaining_cols)
            extra_pixels = remaining_budget % len(remaining_cols)

            if per_col == 0 and extra_pixels == 0:
                break

            next_remaining: list[ColumnConfig] = []
            distributed = 0

            # Distribute the budget among the remaining columns,
            # capping at max_width
            for j, col in enumerate(remaining_cols):
                if not col.name:
                    continue

                adjustment = per_col + (1 if j < extra_pixels else 0)

                # If shrinking, don't go below 0.
                # If stretching, don't go above max_width.
                if do_shrink:
                    new_width = calculated_widths[col.name] - adjustment
                    if new_width < 0:
                        distributed += calculated_widths[col.name]
                        calculated_widths[col.name] = 0
                    else:
                        calculated_widths[col.name] = new_width
                        distributed += adjustment
                        next_remaining.append(col)
                else:
                    new_width = calculated_widths[col.name] + adjustment
                    if new_width > col.max_width:
                        distributed += (col.max_width
                                        - calculated_widths[col.name])
                        calculated_widths[col.name] = col.max_width
                    else:
                        calculated_widths[col.name] = new_width
                        distributed += adjustment
                        next_remaining.append(col)

            remaining_budget -= distributed
            remaining_cols = next_remaining

        # Update shared budget for the next priority group
        self._width_budget = -remaining_budget if do_shrink \
                                               else remaining_budget


# Testing
if __name__ == '__main__':
    column_config = {
        'name': ColumnConfig(
            min_width=10, max_width=40, stretch_priority=1, shrink_priority=4
        ),
        'branch': ColumnConfig(
            min_width=5, max_width=20, stretch_priority=1, shrink_priority=2
        ),
        'status': ColumnConfig(
            min_width=6, max_width=10, stretch_priority=1, shrink_priority=3
        ),
        'github_repo_name': ColumnConfig(
            min_width=5, max_width=30, stretch_priority=1, shrink_priority=1
        ),
    }

    for avaiable_width in [8, 12, 20, 22, 26, 50, 80, 90, 100, 120]:
        adjuster = ColumnWidthsAdjuster(
            column_config=column_config, available_width=80
        )
        adjuster.available_width = avaiable_width
        calculated_widths = adjuster.get_calculated_widths()

        calculated_widths_str = (
            f'name: {calculated_widths['name']}, '
            f'branch: {calculated_widths['branch']}, '
            f'status: {calculated_widths['status']}, '
            f'gitrep: {calculated_widths['github_repo_name']}'
)

        print(f'Available width = {adjuster.available_width} ==> ' \
              + calculated_widths_str)
