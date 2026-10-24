"""Statistics behind the insights (design §4; edge cases #22, #24)."""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from domain.stats import (
    PeerGroup,
    Reason,
    SalaryChange,
    choose_peer_group,
    compa_ratio,
    is_currency_change,
    is_outlier,
    median,
    percentile,
    percentile_excluding,
    percentile_rank,
    raise_percent_between,
    salary_range,
)

BAND = (Decimal("0.80"), Decimal("1.20"))


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


class TestOutliers:
    @pytest.mark.parametrize(
        ("ratio", "expected"), [("0.79", True), ("1.21", True), ("1.0", False)]
    )
    def test_outside_the_band_is_an_outlier(self, ratio: str, expected: bool) -> None:
        assert is_outlier(Decimal(ratio), BAND, peer_count=5, min_group_size=5) is expected

    @pytest.mark.parametrize("ratio", ["0.80", "1.20"])
    def test_the_band_edges_are_inside(self, ratio: str) -> None:
        assert is_outlier(Decimal(ratio), BAND, peer_count=5, min_group_size=5) is False

    def test_a_small_peer_group_never_makes_an_outlier(self) -> None:
        assert is_outlier(Decimal("0.5"), BAND, peer_count=4, min_group_size=5) is False

    def test_no_ratio_is_not_an_outlier(self) -> None:
        assert is_outlier(None, BAND, peer_count=10, min_group_size=5) is False


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


def change(amount: int, currency: str = "INR", reason: Reason = Reason.MERIT) -> SalaryChange:
    return SalaryChange(date(2026, 4, 1), Decimal(amount), currency, reason)


class TestRaisePercent:
    def test_is_the_change_against_the_previous_record(self) -> None:
        assert raise_percent_between(change(1_800_000), change(1_926_000)) == 7

    @pytest.mark.parametrize("reason", [Reason.HIRE, Reason.CORRECTION])
    def test_hire_and_correction_records_are_not_raises(self, reason: Reason) -> None:
        assert raise_percent_between(change(100), change(110, reason=reason)) is None

    def test_a_currency_change_is_not_a_raise_and_is_counted_separately(self) -> None:
        before, after = change(1_800_000, "INR"), change(30_000, "USD", Reason.TRANSFER)

        assert raise_percent_between(before, after) is None
        assert is_currency_change(before, after) is True

    def test_the_first_record_has_no_raise(self) -> None:
        assert raise_percent_between(None, change(100, reason=Reason.HIRE)) is None


class TestPercentileExcluding:
    """Each employee's peers are their group without them (design §4 Peer position)."""

    def test_leaves_out_one_value(self) -> None:
        ordered = decimals(20, 25, 25, 30, 35)
        # Without the 35, the peers are 20, 25, 25, 30: median 25.
        assert percentile_excluding(ordered, 4, Decimal("0.5")) == 25
        # Without the 20: 25, 25, 30, 35, median 27.5.
        assert percentile_excluding(ordered, 0, Decimal("0.5")) == Decimal("27.5")

    def test_a_group_of_one_has_no_peers(self) -> None:
        assert percentile_excluding(decimals(20), 0, Decimal("0.5")) is None

    @given(
        st.lists(st.integers(min_value=1, max_value=10**9), min_size=2, max_size=40),
        st.data(),
        st.sampled_from(["0", "0.1", "0.25", "0.5", "0.75", "0.9", "1"]),
    )
    def test_matches_the_percentile_of_the_list_without_it(
        self, values: list[int], data: st.DataObject, fraction: str
    ) -> None:
        ordered = sorted(Decimal(value) for value in values)
        skip = data.draw(st.integers(min_value=0, max_value=len(ordered) - 1))
        without = ordered[:skip] + ordered[skip + 1 :]

        assert percentile_excluding(ordered, skip, Decimal(fraction)) == percentile(
            without, Decimal(fraction)
        )
