import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re

# Streamlit app title
st.title("Mobile.bg Web Scraper and Analysis")

# User input for base URL
base_url = st.text_input("Enter the base URL for scraping:", "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
headers = {'User-Agent': 'Mozilla/5.0'}

# Prepare empty lists for data
titles_list, prices_list, links_list, probeg_list, skorosti_list, dvigatel_list, moshtnost_list, year_list = [], [], [], [], [], [], [], []

def extract_price(price_div):
    match = re.search(r'(\d+[\s,]?\d*)\s*(лв\.|EUR)', price_div)
    if not match:
        return None
    price = float(match.group(1).replace(',', '').replace(' ', ''))
    currency = match.group(2)
    if 'Цената е без ДДС' in price_div:
        price *= 1.2  # Add 20% VAT
    if currency == 'EUR':
        price *= 1.95  # EUR to BGN conversion rate
    return price

def extract_individual_data(url):
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

if base_url:
    # Scrape data
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
            price_value = extract_price(price.text.strip())
            if price_value:
                titles_list.append(title.text.strip())
                prices_list.append(price_value)
                links_list.append("https:" + title['href'])
                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'])
                probeg_list.append(probeg)
                skorosti_list.append(skorosti)
                dvigatel_list.append(dvigatel)
                moshtnost_list.append(moshtnost)
                year_list.append(year)
        page += 1

    # Create DataFrame
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

    # Display raw data table
    st.write("### Scraped Data Table", df)

    # Aggregated data
    st.write("### Aggregated Data")
    max_price = max(prices_list)
    min_price = min(prices_list)
    st.write(f"Maximum Price: {max_price:.2f} лв.")
    st.write(f"Minimum Price: {min_price:.2f} лв.")
    st.write(f"Average Price: {statistics.mean(prices_list):.2f} лв.")
    st.write(f"Median Price: {statistics.median(prices_list):.2f} лв.")

    # Visualizations
    st.write("### Visualizations")

    # Histogram
    st.bar_chart(df['Price (лв.)'])

    # Pie chart
    st.write("#### Listings by Скоростна кутия")
    st.bar_chart(df["Скоростна кутия"].value_counts())

    st.write("#### Listings by Двигател")
    st.bar_chart(df["Двигател"].value_counts())
