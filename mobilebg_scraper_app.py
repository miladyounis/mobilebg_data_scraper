
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re

st.title("Mobile.bg Scraper and Analyzer")

# User input for base URL
base_url = st.text_input("Enter the base URL for scraping:", "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
headers = {'User-Agent': 'Mozilla/5.0'}

if base_url:
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

    # Scrape data from multiple pages
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

    # Create DataFrame and display
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
    st.dataframe(df)

    # Save DataFrame to CSV
    filename = f"{base_url.split('/')[-1]}_listings_with_details_readable.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    st.success(f"Data saved to {filename}")

    # Display aggregated data
    if prices_list:
        max_price = max(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
        min_price = min(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
        average_price = statistics.mean([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
        median_price = statistics.median([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
        st.write("### Aggregated Data")
        st.write(f"**Total Listings:** {len(prices_list)}")
        st.write(f"**Maximum Price:** {max_price}")
        st.write(f"**Minimum Price:** {min_price}")
        st.write(f"**Average Price:** {average_price:.2f} лв.")
        st.write(f"**Median Price:** {median_price:.2f} лв.")

        # Visualization: Price Distribution
        st.write("### Price Distribution")
        prices_numeric = [float(p.replace(' лв.', '').replace(',', '')) for p in prices_list]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(prices_numeric, bins=20, edgecolor='black', color="#0070F2")
        ax.set_title('Price Distribution', fontsize=16, fontweight='bold')
        ax.set_xlabel('Price (лв.)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=14, fontweight='bold')
        st.pyplot(fig)

        # Pie charts for "Скоростна кутия" and "Двигател"
        st.write("### Listings by Скоростна кутия and Двигател")
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))

        # Скоростна кутия Pie Chart
        skorosti_counts = pd.Series(skorosti_list).value_counts()
        axes[0].pie(skorosti_counts, labels=skorosti_counts.index, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 12})
        axes[0].set_title("Скоростна кутия", fontsize=14, fontweight='bold')

        # Двигател Pie Chart
        dvigatel_counts = pd.Series(dvigatel_list).value_counts()
        axes[1].pie(dvigatel_counts, labels=dvigatel_counts.index, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 12})
        axes[1].set_title("Двигател", fontsize=14, fontweight='bold')

        st.pyplot(fig)

        # Scatter plot for Price vs. Mileage
        st.write("### Price vs. Mileage")
        probeg_numeric = [float(p.replace(' км', '').replace(',', '').replace(' ', '')) for p in probeg_list if p]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(probeg_numeric, prices_numeric, alpha=0.7)
        ax.set_title("Price vs. Mileage", fontsize=16, fontweight='bold')
        ax.set_xlabel("Mileage (km)", fontsize=14, fontweight='bold')
        ax.set_ylabel("Price (лв.)", fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)

# Display message if no base URL is entered
else:
    st.warning("Please enter a base URL to start scraping.")
