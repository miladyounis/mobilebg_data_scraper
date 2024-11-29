import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import statistics
import matplotlib.pyplot as plt

# Helper functions
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

def extract_individual_data(url, headers):
    response = requests.get(url, headers=headers)
    response.encoding = 'windows-1251'
    soup = BeautifulSoup(response.text, "html.parser")
    
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
    
    items = soup.find("div", class_="items")
    year = None
    if items:
        for item in items.find_all("div", class_="item"):
            if "Дата на производство" in item.text:
                year_match = re.search(r"(\d{4})", item.text)
                if year_match:
                    year = year_match.group(1)
    
    return probeg, skorosti, dvigatel, moshtnost, year

# Streamlit app
st.title("Car Listings Web Scraper")
st.markdown("This app scrapes car listings from the specified base URL and provides insights with visualizations and a downloadable dataset.")

base_url = st.text_input("Enter the base URL for the car listings:", placeholder="e.g., https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")

if base_url:
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    titles_list = []
    prices_list = []
    links_list = []
    probeg_list = []
    skorosti_list = []
    dvigatel_list = []
    moshtnost_list = []
    year_list = []

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
                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'], headers)
                probeg_list.append(probeg)
                skorosti_list.append(skorosti)
                dvigatel_list.append(dvigatel)
                moshtnost_list.append(moshtnost)
                year_list.append(year)

        page += 1

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

    st.subheader("Scraped Data")
    st.dataframe(df)

    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(label="Download CSV", data=csv, file_name='car_listings.csv', mime='text/csv')

    # Convert price strings to numeric for calculations
    prices_numeric = []
    for price in prices_list:
        try:
            numeric_price = float(price.replace(' лв.', '').replace(',', ''))
            prices_numeric.append(numeric_price)
        except ValueError:
            continue

    # Aggregated data
    if prices_numeric:
        max_price = max(prices_numeric)
        min_price = min(prices_numeric)
        max_price_link = df[df["Price (лв.)"].astype(str) == f"{max_price:.2f} лв."]["Link"].values[0]
        min_price_link = df[df["Price (лв.)"].astype(str) == f"{min_price:.2f} лв."]["Link"].values[0]

        st.subheader("Aggregated Data")
        st.write(f"**Total Listings:** {len(prices_list)}")
        st.write(f"**Maximum Price:** {max_price:.2f} лв. ([Link]({max_price_link}))")
        st.write(f"**Minimum Price:** {min_price:.2f} лв. ([Link]({min_price_link}))")
        average_price = statistics.mean(prices_numeric)
        st.write(f"**Average Price:** {average_price:.2f} лв.")
        median_price = statistics.median(prices_numeric)
        st.write(f"**Median Price:** {median_price:.2f} лв.")

    st.subheader("Visualizations")

    if prices_numeric:
        st.write("### Price Distribution")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(prices_numeric, bins=20, edgecolor='black', color="#0070F2")
        ax.set_title('Price Distribution', fontsize=16, fontweight='bold')
        ax.set_xlabel('Price (лв.)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=14, fontweight='bold')
        st.pyplot(fig)

    # Listings by Скоростна кутия
    st.write("### Listings by Скоростна кутия")
    skorosti_counts = pd.Series(skorosti_list).value_counts()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.pie(skorosti_counts, labels=skorosti_counts.index, autopct='%1.1f%%', startangle=140)
    ax.set_title("Listings by Скоростна кутия", fontsize=14, fontweight='bold')
    st.pyplot(fig)

    # Listings by Двигател
    st.write("### Listings by Двигател")
    dvigatel_counts = pd.Series(dvigatel_list).value_counts()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.pie(dvigatel_counts, labels=dvigatel_counts.index, autopct='%1.1f%%', startangle=140)
    ax.set_title("Listings by Двигател", fontsize=14, fontweight='bold')
    st.pyplot(fig)

    # Price vs. Mileage
    probeg_numeric = [float(p.replace(' км', '').replace(',', '').replace(' ', '')) for p in probeg_list if p is not None]
    if prices_numeric and probeg_numeric:
        st.write("### Price vs. Mileage")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(probeg_numeric, prices_numeric[:len(probeg_numeric)], alpha=0.7)
        ax.set_title("Price vs. Mileage", fontsize=16, fontweight='bold')
        ax.set_xlabel("Mileage (km)", fontsize=14, fontweight='bold')
        ax.set_ylabel("Price (лв.)", fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)

    # Number of Cars per Year
    year_counts = pd.Series(year_list).value_counts().sort_index()
    if not year_counts.empty:
        st.write("### Number of Cars per Year")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(year_counts.index, year_counts.values, color='skyblue', edgecolor='black')
        ax.set_title('Number of Cars per Year', fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontsize=14, fontweight='bold')
        ax.set_ylabel('Number of Cars', fontsize=14, fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        st.pyplot(fig)

    # Price vs. Year Correlation
    sorted_data = sorted(zip(year_list, prices_list), key=lambda x: (int(x[0]), float(x[1].replace(' лв.', '').replace(',', ''))))
    sorted_years, sorted_prices = zip(*sorted_data)
    sorted_prices_numeric = [float(price.replace(' лв.', '').replace(',', '')) for price in sorted_prices]
    if sorted_prices_numeric:
        st.write("### Price vs. Year Correlation")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(sorted_years, sorted_prices_numeric, alpha=0.7, color='blue')
        ax.set_title('Price vs. Year Correlation', fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontsize=14, fontweight='bold')
        ax.set_ylabel('Price (лв.)', fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)
