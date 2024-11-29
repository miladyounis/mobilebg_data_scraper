import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re

# Base URL
base_url = "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60"
headers = {'User-Agent': 'Mozilla/5.0'}

# Prepare empty lists for data
titles_list = []
prices_list = []
links_list = []
probeg_list = []
skorosti_list = []
dvigatel_list = []
moshtnost_list = []
year_list = []

def extract_price(price_div):
    match = re.search(r'(\d+[\s,]?\d*)\s*(лв\.|EUR)', price_div)
    if not match:
        return None

    price = float(match.group(1).replace(',', '').replace(' ', ''))
    currency = match.group(2)

    if 'Цената е без ДДС' in price_div:
        price *= 1.2  # Add 20% VAT
        return f"{price:.2f} лв."

    if currency == 'EUR':
        price *= 1.95  # EUR to BGN conversion rate
        return f"{price:.2f} лв."

    return f"{price:.2f} лв."

def extract_individual_data(url):
    response = requests.get(url, headers=headers)
    response.encoding = 'windows-1251'
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract mainCarParams data
    main_params = soup.find("div", class_="mainCarParams")
    probeg = skorosti = dvigatel = moshtnost = None
    if main_params:
        for item in main_params.find_all("div", class_="item"):
            label = item.find("div", class_="mpLabel").text.strip()
            info = item.find("div", class_="mpInfo").text.strip()
            if label == "Пробег [км]":
                probeg = info
            elif label == "Скоростна кутия":
                skorosti = info
            elif label == "Двигател":
                dvigatel = info
            elif label == "Мощност":
                moshtnost = info
    
    # Extract year of production
    items = soup.find("div", class_="items")
    year = None
    if items:
        for item in items.find_all("div", class_="item"):
            if "Дата на производство" in item.text:
                year_match = re.search(r"(\d{4})", item.text)
                if year_match:
                    year = year_match.group(1)
    
    return probeg, skorosti, dvigatel, moshtnost, year

# Loop through pages
page = 1
while True:
    url = f"{base_url}/p-{page}" if page > 1 else base_url
    response = requests.get(url, headers=headers)
    response.encoding = 'windows-1251'
    soup = BeautifulSoup(response.text, "html.parser")

    titles = soup.find_all("a", class_="title")
    prices = soup.find_all("div", class_="price")

    if not titles:
        break

    for title, price in zip(titles, prices):
        price_text = price.text.strip()
        processed_price = extract_price(price_text)
        if processed_price:
            titles_list.append(title.text.strip())
            prices_list.append(processed_price)
            links_list.append("https:" + title['href'])
            
            # Extract data from the individual page
            probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'])
            probeg_list.append(probeg)
            skorosti_list.append(skorosti)
            dvigatel_list.append(dvigatel)
            moshtnost_list.append(moshtnost)
            year_list.append(year)

    page += 1

# Create DataFrame and save to CSV
df = pd.DataFrame({
    "Title": titles_list,
    "Price (лв.)": prices_list,
    "Link": links_list,
    "Пробег": probeg_list,
    "Скоростна кутия": skorosti_list,
    "Двигател": dvigatel_list,
    "Мощност": moshtnost_list,
    "Year": year_list
})
df.to_csv(f"{base_url.split('/')[-1]}_listings_with_details_readable.csv", index=False, encoding='utf-8-sig')

# Aggregated data
max_price = max(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
min_price = min(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
max_price_link = df[df["Price (лв.)"] == max_price]["Link"].values[0]
min_price_link = df[df["Price (лв.)"] == min_price]["Link"].values[0]

print("\nAggregated Data:")
print(f"Total Listings: {len(prices_list)}")
print(f"Maximum Price: {max_price} (Link: {max_price_link})")
print(f"Minimum Price: {min_price} (Link: {min_price_link})")
average_price = statistics.mean([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
print(f"Average Price: {average_price:.2f} лв.")
median_price = statistics.median([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
print(f"Median Price: {median_price:.2f} лв.")

# Visualization part
plt.figure(figsize=(20, 5))

# Histogram
plt.subplot(1, 2, 1)
plt.hist([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list], bins=20, edgecolor='black', color="#0070F2")
plt.title('Price Distribution', fontsize=16, fontweight='bold')
plt.xlabel('Price (лв.)', fontsize=14, fontweight='bold')
plt.ylabel('Frequency', fontsize=14, fontweight='bold')

# Pie chart for "Скоростна кутия"
plt.figure(figsize=(12, 6))

# Data preparation
skorosti_counts = pd.Series(skorosti_list).value_counts()

# Pie chart
plt.subplot(1, 2, 1)
plt.pie(skorosti_counts, labels=skorosti_counts.index, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 12})
plt.title("Listings by Скоростна кутия", fontsize=14, fontweight='bold')

# Pie chart for "Двигател"
dvigatel_counts = pd.Series(dvigatel_list).value_counts()

# Pie chart
plt.subplot(1, 2, 2)
plt.pie(dvigatel_counts, labels=dvigatel_counts.index, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 12})
plt.title("Listings by Двигател", fontsize=14, fontweight='bold')

# Scatter plot for Price vs. Mileage
plt.figure(figsize=(10, 6))

# Data preparation
prices_numeric = [float(p.replace(' лв.', '').replace(',', '')) for p in prices_list]
probeg_numeric = [float(p.replace(' км', '').replace(',', '').replace(' ', '')) for p in probeg_list if p is not None]

# Scatter plot
plt.scatter(probeg_numeric, prices_numeric, alpha=0.7)
plt.title("Price vs. Mileage", fontsize=16, fontweight='bold')
plt.xlabel("Mileage (km)", fontsize=14, fontweight='bold')
plt.ylabel("Price (лв.)", fontsize=14, fontweight='bold')
plt.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.show()

# Sort data by year in ascending order
sorted_data = sorted(zip(year_list, prices_list))
year_list_sorted, prices_list_sorted = zip(*sorted_data)

# Visualization 1: Cars per Year
plt.figure(figsize=(10, 6))
plt.hist(year_list_sorted, bins=len(set(year_list_sorted)), edgecolor='black', color='skyblue')
plt.title('Number of Cars per Year', fontsize=16, fontweight='bold')
plt.xlabel('Year', fontsize=14, fontweight='bold')
plt.ylabel('Number of Cars', fontsize=14, fontweight='bold')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()

# Visualization 2: Price vs. Year Correlation (Both Sorted in Ascending Order)
plt.figure(figsize=(10, 6))

# Sort both year and price in ascending order together
sorted_year_price = sorted(zip(year_list_sorted, prices_list_sorted), key=lambda x: (int(x[0]), float(x[1].replace(' лв.', '').replace(',', ''))))
sorted_years, sorted_prices = zip(*sorted_year_price)

# Convert prices to numeric
sorted_prices_numeric = [float(price.replace(' лв.', '').replace(',', '')) for price in sorted_prices]

# Scatter plot
plt.scatter(sorted_years, sorted_prices_numeric, alpha=0.7, color='blue')
plt.title('Price vs. Year Correlation (Both Sorted in Ascending Order)', fontsize=16, fontweight='bold')
plt.xlabel('Year', fontsize=14, fontweight='bold')
plt.ylabel('Price (лв.)', fontsize=14, fontweight='bold')
plt.grid(True, linestyle='--', alpha=0.5)
plt.show()
