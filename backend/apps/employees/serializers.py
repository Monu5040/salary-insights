from typing import Any

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
    """One row of the directory, with the salary at its currency's decimals."""

    country = CountryRef(read_only=True)
    department = DepartmentRef(read_only=True)
    salary = serializers.SerializerMethodField()
    currency = serializers.CharField(source="currency_id", read_only=True)

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

    def get_salary(self, employee: Employee) -> str:
        return money_text(employee.salary, employee.currency.minor_units)


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
    salary = AmountField(max_length=40, help_text="Annual gross base salary, as a string")
    currency = serializers.SlugRelatedField(slug_field="code", queryset=Currency.objects.all())

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
            "salary",
            "currency",
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

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """The salary must fit its currency: its decimals and its typo ceiling (#7, #8).

        An edit may send only one of the two, so the other comes from the record."""
        if "salary" not in attrs and "currency" not in attrs:
            return attrs
        current = self.instance
        currency: Currency = attrs.get("currency") or current.currency  # type: ignore[union-attr]
        raw = attrs.get("salary")
        if raw is None:
            raw = money_text(current.salary, current.currency.minor_units)  # type: ignore[union-attr]
        try:
            attrs["salary"] = parse_amount(raw, currency.minor_units, currency.salary_ceiling)
        except InvalidAmount as error:
            raise serializers.ValidationError({"salary": [str(error)]}) from None
        return attrs
