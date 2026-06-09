import pandas as pd
import random
from datetime import datetime, timedelta

products = ["Acoustic Guitar XT200", "Bose Ultra Headphones", "Logitech MX Master 3S", "Dell UltraSharp 27 Monitor", "Apple MacBook Air M2", "Sony Alpha a7 IV", "Nike Air Force 1", "Kindle Paperwhite 16GB", "Nintendo Switch OLED", "Herman Miller Aeron Chair"]
data = []
base_date = datetime(2024, 1, 1)

for i in range(200):
    prod = random.choice(products)
    data.append({
        "Date": (base_date + timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
        "Product_Name": prod,
        "Sales_Quantity": random.randint(1, 20),
        "Revenue": random.randint(100, 2000),
        "Region": random.choice(["North", "South", "East", "West"])
    })

df = pd.DataFrame(data)
df.to_csv("c:/Users/lenovo/Desktop/DGUpdatedProject/demo_sales_with_products.csv", index=False)
print("Dataset created: demo_sales_with_products.csv")
