"""Statistics behind the insights (design §4; edge cases #22, #24)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from domain.stats import (
    PeerGroup,
    choose_peer_group,
    compa_ratio,
    median,
    percentile,
    percentile_rank,
    salary_range,
)


def decimals(*values: int | str) -> list[Decimal]:
    return [Decimal(value) for value in values]


class TestPercentile:
    """Linear interpolation between closest ranks, the same as PostgreSQL's percentile_cont."""

    @pytest.mark.parametrize(
        ("fraction", "expected"), [("0", 10), ("0.1", 13), ("0.5", 25), ("0.9", 37), ("1", 40)]
    )
    def test_interpolates_like_percentile_cont(self, fraction: str, expected: int) -> None:
        assert percentile(decimals(40, 10, 30, 20), Decimal(fraction)) == expected

    def test_median_is_the_fiftieth_percentile(self) -> None:
        assert median(decimals(1, 2, 3, 10)) == Decimal("2.5")

    def test_a_single_value_is_every_percentile(self) -> None:
        assert percentile(decimals(42), Decimal("0.9")) == 42

    def test_no_values_means_no_percentile(self) -> None:
        assert percentile([], Decimal("0.5")) is None

    @pytest.mark.parametrize("fraction", ["-0.1", "1.1"])
    def test_fraction_must_be_between_zero_and_one(self, fraction: str) -> None:
        with pytest.raises(ValueError, match="between 0 and 1"):
            percentile(decimals(1, 2), Decimal(fraction))

    @given(
        st.lists(st.decimals(min_value=1, max_value=10**9, places=2), min_size=1, max_size=50),
        st.decimals(min_value=0, max_value=1, places=3),
        st.decimals(min_value=0, max_value=1, places=3),
    )
    def test_stays_within_the_data_and_never_decreases(
        self, values: list[Decimal], a: Decimal, b: Decimal
    ) -> None:
        low, high = sorted([a, b])
        p_low, p_high = percentile(values, low), percentile(values, high)
        assert p_low is not None and p_high is not None
        assert min(values) <= p_low <= p_high <= max(values)


class TestSalaryRange:
    def test_reports_n_and_the_five_percentiles(self) -> None:
        result = salary_range([Decimal(1000 * i) for i in range(1, 11)], min_group_size=5)

        assert result.n == 10
        percentiles = [result.p10, result.p25, result.median, result.p75, result.p90]
        assert percentiles == decimals(1900, 3250, 5500, 7750, 9100)
        assert result.low_sample is False

    def test_flags_groups_smaller_than_the_minimum(self) -> None:
        assert salary_range(decimals(1, 2, 3), min_group_size=5).low_sample is True

    def test_an_empty_group_has_null_statistics(self) -> None:
        result = salary_range([], min_group_size=5)

        assert result.n == 0
        assert result.median is None
        assert result.low_sample is True


class TestPeerPosition:
    def test_percentile_rank_is_the_share_of_peers_paid_less(self) -> None:
        assert percentile_rank(Decimal(50), decimals(10, 20, 30, 40, 60, 70, 80, 90)) == 50

    def test_ties_count_half(self) -> None:
        assert percentile_rank(Decimal(50), decimals(10, 50, 50, 90)) == 50

    def test_ranges_from_zero_to_one_hundred(self) -> None:
        assert percentile_rank(Decimal(1), decimals(5, 6)) == 0
        assert percentile_rank(Decimal(9), decimals(5, 6)) == 100

    def test_no_peers_means_no_rank(self) -> None:
        assert percentile_rank(Decimal(50), []) is None

    def test_compa_ratio_is_salary_over_the_peer_median(self) -> None:
        assert compa_ratio(Decimal(110000), Decimal(100000)) == Decimal("1.1")
        assert compa_ratio(Decimal(110000), None) is None


class TestPeerGroup:
    TITLE = PeerGroup("country + level + job title", size=3)
    DEPARTMENT = PeerGroup("country + level + department", size=7)
    LEVEL = PeerGroup("country + level", size=40)

    def test_falls_back_to_the_first_definition_with_enough_people(self) -> None:
        chosen = choose_peer_group([self.TITLE, self.DEPARTMENT, self.LEVEL], min_group_size=5)
        assert chosen == self.DEPARTMENT

    def test_keeps_the_narrowest_definition_when_it_is_big_enough(self) -> None:
        big_title = PeerGroup("country + level + job title", size=12)
        assert choose_peer_group([big_title, self.LEVEL], min_group_size=5) == big_title

    def test_uses_the_broadest_definition_when_none_is_big_enough(self) -> None:
        tiny = PeerGroup("country + level", size=2)
        assert choose_peer_group([self.TITLE, tiny], min_group_size=5) == tiny

    def test_needs_at_least_one_definition(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            choose_peer_group([], min_group_size=5)
