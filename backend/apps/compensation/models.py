from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint

from domain.stats import Reason


class SalaryRecord(models.Model):
    """One effective-dated annual salary. The salary on a date is the latest record on or
    before it (design D4, §4), so back-dated and future-dated changes need no sync job."""

    # db_index=False: the unique (employee, effective_date) index already starts with employee.
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="salary_records",
        db_index=False,
    )
    effective_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4, help_text="Annual gross base")
    currency = models.ForeignKey("reference.Currency", on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(
        max_length=16, choices=[(reason.value, reason.value.capitalize()) for reason in Reason]
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "salary_records"
        ordering = ["employee", "-effective_date"]
        constraints = [
            # Also the index behind "the latest record on or before a date" (design §3).
            UniqueConstraint(
                F("employee"), F("effective_date").desc(), name="salary_record_one_per_day"
            ),
            CheckConstraint(condition=Q(amount__gt=0), name="salary_record_amount_positive"),
            CheckConstraint(
                condition=Q(reason__in=[reason.value for reason in Reason]),
                name="salary_record_reason_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} from {self.effective_date}: {self.amount} {self.currency_id}"
