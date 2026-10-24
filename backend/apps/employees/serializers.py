from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.pagination import PageQuery
from apps.employees.models import Employee
from apps.employees.selectors import SORTS
from apps.reference.models import Country, Currency, Department
from domain.money import InvalidAmount, money_text, parse_amount
from domain.text import InvalidCode, clean_name, employee_code


class DirectoryQuery(PageQuery):
    """The directory's query string. Anything not listed here is refused (edge case #21)."""

    q = serializers.CharField(required=False, allow_blank=True, max_length=100, default="")
    country = serializers.ListField(child=serializers.CharField(max_length=2), default=list)
    department = serializers.ListField(child=serializers.IntegerField(), default=list)
    sort = serializers.ChoiceField(
        choices=[*SORTS, *(f"-{key}" for key in SORTS)], default="full_name"
    )


class CountryRef(serializers.ModelSerializer[Country]):
    class Meta:
        model = Country
        fields = ["code", "name"]


class DepartmentRef(serializers.ModelSerializer[Department]):
    class Meta:
        model = Department
        fields = ["id", "name"]


class AmountField(serializers.CharField):
    """Money arrives as a string such as "85000.50", never a JSON number (design D5)."""

    default_error_messages = {"not_text": 'Send the amount as a string, such as "85000.50".'}

    def to_internal_value(self, data: Any) -> str:
        if not isinstance(data, str):
            self.fail("not_text")
        return super().to_internal_value(data)


class EmployeeRowSerializer(serializers.ModelSerializer[Employee]):
    """One row of the directory, with the salary in force today at its currency's decimals.

    Needs the rows from selectors.employees(), which adds that salary."""

    country = CountryRef(read_only=True)
    department = DepartmentRef(read_only=True)
    salary = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_code",
            "full_name",
            "country",
            "department",
            "job_title",
            "hire_date",
            "salary",
            "currency",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_salary(self, employee: Employee) -> str | None:
        amount = getattr(employee, "salary_amount", None)
        if amount is None:
            return None  # only before their first salary takes effect
        return money_text(amount, employee.salary_minor_units)  # type: ignore[attr-defined]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_currency(self, employee: Employee) -> str | None:
        return getattr(employee, "salary_currency", None)


class EmployeeSerializer(EmployeeRowSerializer):
    """The whole record, with the version a write sends back in If-Match."""

    class Meta(EmployeeRowSerializer.Meta):
        fields = [*EmployeeRowSerializer.Meta.fields, "email", "version", "updated_at"]


class EmployeePage(serializers.Serializer[Any]):
    """The directory's response (for the API schema)."""

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = EmployeeRowSerializer(many=True)


class EmployeeWriteSerializer(serializers.ModelSerializer[Employee]):
    """What the HR manager may set. id, version and timestamps aren't here, so a client
    can't set them (edge case #14)."""

    employee_code = serializers.CharField(max_length=40)
    country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())

    class Meta:
        model = Employee
        fields = [
            "employee_code",
            "full_name",
            "email",
            "country",
            "department",
            "job_title",
            "hire_date",
        ]
        # Uniqueness is left to the database, and a clash is a 409 naming the field (#10).
        validators: list[Any] = []

    def validate_employee_code(self, value: str) -> str:
        try:
            return employee_code(value)
        except InvalidCode as error:
            raise serializers.ValidationError(str(error)) from None

    def validate_full_name(self, value: str) -> str:
        return clean_name(value)


class NewEmployeeSerializer(EmployeeWriteSerializer):
    """A new employee with their starting salary, effective on the hire date. Later changes
    go through the salary history."""

    salary = AmountField(max_length=40, help_text="Annual gross base salary, as a string")
    currency = serializers.SlugRelatedField(slug_field="code", queryset=Currency.objects.all())

    class Meta(EmployeeWriteSerializer.Meta):
        fields = [*EmployeeWriteSerializer.Meta.fields, "salary", "currency"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """The salary must fit its currency: its decimals and its typo ceiling (#2, #7)."""
        currency: Currency = attrs["currency"]
        try:
            attrs["salary"] = parse_amount(
                attrs["salary"], currency.minor_units, currency.salary_ceiling
            )
        except InvalidAmount as error:
            raise serializers.ValidationError({"salary": [str(error)]}) from None
        return attrs
