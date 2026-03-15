import pytest
from git_repo_jumper.cli.output import str_with_fixed_width


class TestStrWithFixedWidth:
    def test_truncate_from_right_by_default(self):
        result = str_with_fixed_width('Hello, World!', 10)
        assert result == 'Hello, Wo…'

    def test_truncated_string_has_correct_length(self):
        result = str_with_fixed_width('Hello, World!', 10)
        assert len(result) == 10

    def test_pad_left_alignment(self):
        result = str_with_fixed_width('Hi', 5)
        assert result == 'Hi   '

    def test_pad_left_has_correct_length(self):
        result = str_with_fixed_width('Hi', 5)
        assert len(result) == 5

    def test_pad_right_alignment(self):
        result = str_with_fixed_width('Hi', 5, align='right')
        assert result == '   Hi'

    def test_pad_right_has_correct_length(self):
        result = str_with_fixed_width('Hi', 5, align='right')
        assert len(result) == 5

    def test_pad_center_alignment(self):
        result = str_with_fixed_width('Hi', 6, align='center')
        assert result == '  Hi  '

    def test_pad_center_has_correct_length(self):
        result = str_with_fixed_width('Hi', 6, align='center')
        assert len(result) == 6

    def test_truncate_right_align_from_left(self):
        result = str_with_fixed_width('Hello, World!', 10, align='right')
        assert result == '…o, World!'

    def test_truncate_right_align_has_correct_length(self):
        result = str_with_fixed_width('Hello, World!', 10, align='right')
        assert len(result) == 10

    def test_exact_length_unchanged(self):
        result = str_with_fixed_width('Hello', 5)
        assert result == 'Hello'

    def test_empty_string_padded_with_spaces(self):
        result = str_with_fixed_width('', 3)
        assert result == '   '

    def test_invalid_alignment_raises_value_error(self):
        with pytest.raises(ValueError):
            str_with_fixed_width('Hello', 5, align='diagonal')
