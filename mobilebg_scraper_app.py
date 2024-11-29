import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re

# Set page configuration
st.set_page_config(page_title="Volvo XC60 Listings", layout="wide")

# Base URL and headers
base_url = "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60"
headers = {'User-Agent': 'Mozilla/5.0'}

# Function to extract price
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

# Function to extract individual data
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

# Scraping logic
@st.cache_data
def scrape_data():
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
                
                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'])
                probeg_list.append(probeg)
                skorosti_list.append(skorosti)
                dvigatel_list.append(dvigatel)
                moshtnost_list.append(moshtnost)
                year_list.append(year)
    
        page += 1
    
    return pd.DataFrame({
        "Title": titles_list,
        "Price (лв.)": prices_list,
        "Link": links_list,
        "Пробег": probeg_list,
        "Скоростна кутия": skorosti_list,
        "Двигател": dvigatel_list,
        "Мощност": moshtnost_list,
        "Year": year_list
    })

# Display data
st.title("Volvo XC60 Listings Analysis")
df = scrape_data()
st.write("### Scraped Data")
st.dataframe(df)

# Aggregated Data
prices_numeric = [float(p.replace(' лв.', '').replace(',', '')) for p in df["Price (лв.)"]]
st.sidebar.write("### Aggregated Data")
st.sidebar.write(f"Total Listings: {len(prices_numeric)}")
st.sidebar.write(f"Max Price: {max(prices_numeric):,.2f} лв.")
st.sidebar.write(f"Min Price: {min(prices_numeric):,.2f} лв.")
st.sidebar.write(f"Average Price: {statistics.mean(prices_numeric):,.2f} лв.")
st.sidebar.write(f"Median Price: {statistics.median(prices_numeric):,.2f} лв.")

# Visualizations
st.write("### Visualizations")

# Histogram of Prices
st.write("#### Price Distribution")
fig, ax = plt.subplots()
ax.hist(prices_numeric, bins=20, edgecolor='black', color="#0070F2")
ax.set_title("Price Distribution", fontsize=16, fontweight='bold')
ax.set_xlabel("Price (лв.)", fontsize=14, fontweight='bold')
ax.set_ylabel("Frequency", fontsize=14, fontweight='bold')
st.pyplot(fig)

# Pie Chart for Скоростна кутия
st.write("#### Listings by Скоростна кутия")
skorosti_counts = df["Скоростна кутия"].value_counts()
fig, ax = plt.subplots()
ax.pie(skorosti_counts, labels=skorosti_counts.index, autopct='%1.1f%%', startangle=140)
ax.set_title("Listings by Скоростна кутия", fontsize=14, fontweight='bold')
st.pyplot(fig)
