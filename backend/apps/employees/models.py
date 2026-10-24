from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.db.models.functions import Lower


class Employee(models.Model):
    """A full-time employee and their current annual base salary (design D4)."""

    employee_code = models.CharField(max_length=32, unique=True, help_text="HR's own key")
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    # db_index=False: the employee_filters index already starts with country.
    country = models.ForeignKey(
        "reference.Country", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    department = models.ForeignKey(
        "reference.Department", on_delete=models.PROTECT, related_name="+"
    )
    job_title = models.CharField(max_length=120)
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=19, decimal_places=4, help_text="Annual gross base")
    currency = models.ForeignKey("reference.Currency", on_delete=models.PROTECT, related_name="+")
    search_text = models.TextField(editable=False, help_text="domain.text.fold(name + code)")
    version = models.PositiveIntegerField(default=1, help_text="Optimistic locking (If-Match)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees"
        ordering = ["full_name", "id"]
        constraints = [
            UniqueConstraint(Lower("email"), name="employee_email_unique_ci"),
            CheckConstraint(condition=Q(full_name__regex=r"\S"), name="employee_name_not_blank"),
            CheckConstraint(
                condition=Q(employee_code__regex=r"\S"), name="employee_code_not_blank"
            ),
            CheckConstraint(condition=Q(salary__gt=0), name="employee_salary_positive"),
        ]
        indexes = [
            models.Index(fields=["country", "department"], name="employee_filters"),
            models.Index(fields=["job_title"], name="employee_job_title"),
            GinIndex(fields=["search_text"], opclasses=["gin_trgm_ops"], name="employee_search"),
        ]

    def __str__(self) -> str:
        return f"{self.employee_code} {self.full_name}"
