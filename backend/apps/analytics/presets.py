"""The dashboard's questions (design §2 Configuration).

Each is a saved explorer query, so changing what the dashboard asks means changing this
list, not code. `chart` says how the screen draws it: bars, ranges or a table.
"""

PRESETS = [
    {
        "id": "payroll-by-country",
        "title": "Payroll by country",
        "chart": "bars",
        "metrics": ["payroll"],
        "by": ["country"],
    },
    {
        "id": "payroll-by-department",
        "title": "Payroll by department",
        "chart": "bars",
        "metrics": ["payroll"],
        "by": ["department"],
    },
    {
        "id": "ranges-by-country",
        "title": "Salary ranges by country",
        "chart": "ranges",
        "metrics": ["p10", "p25", "median", "p75", "p90"],
        "by": ["country"],
    },
    {
        "id": "ranges-by-department",
        "title": "Salary ranges by department",
        "chart": "ranges",
        "metrics": ["p10", "p25", "median", "p75", "p90"],
        "by": ["department"],
    },
    {
        "id": "salary-by-job-title",
        "title": "Salary by job title",
        "chart": "table",
        "metrics": ["headcount", "min", "median", "mean", "max"],
        "by": ["title"],
    },
]
