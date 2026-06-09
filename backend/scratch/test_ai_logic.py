import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from ai_manager import get_kpi_analysis

metrics = [
    {"name": "sales", "value": 1000},
    {"name": "returns", "value": 50}
]

print("Starting AI Test...")
result = get_kpi_analysis(metrics)
print("Result:", result)
