import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re
from requests.exceptions import RequestException
import time

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

# Function to extract individual page data
def extract_individual_data(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'windows-1251'
        soup = BeautifulSoup(response.text, "html.parser")
    except RequestException as e:
        st.warning(f"Failed to fetch individual data from {url}. Error: {e}")
        return None, None, None, None, None

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

# Streamlit App
st.title("Mobile.bg Car Listings Scraper")

# User input for base URL
base_url = st.text_input("Enter the base URL for the car listings", "")

if base_url:
    st.write("Scraping data...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    titles_list, prices_list, links_list, probeg_list = [], [], [], []
    skorosti_list, dvigatel_list, moshtnost_list, year_list = [], [], [], []

    # Loop through pages
    page = 1
    while True:
        url = f"{base_url}/p-{page}" if page > 1 else base_url
        for attempt in range(3):  # Retry logic
            try:
                response = requests.get(url, headers=headers)
                response.encoding = 'windows-1251'
                if response.status_code == 200:
                    break
            except RequestException as e:
                if attempt == 2:
                    st.error(f"Failed to connect to {url}. Error: {e}")
                    break
                time.sleep(2)

        soup = BeautifulSoup(response.text, "html.parser")
        
        titles = soup.find_all("a", class_="title")
        prices = soup.find_all("div", class_="price")
        
        if not titles or not prices:
            st.warning("No listings found on this page. Please check the base URL or try again later.")
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
    
    # Display DataFrame
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
    
    st.write(df)

    # Save to CSV
    csv_file = f"{base_url.split('/')[-1]}_listings_with_details.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    st.write(f"Data saved to {csv_file}")

    # Aggregated Data
    st.header("Aggregated Data")
    if prices_list:
        max_price = max(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
        min_price = min(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
        average_price = statistics.mean([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
        median_price = statistics.median([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])

        st.write(f"Total Listings: {len(prices_list)}")
        st.write(f"Maximum Price: {max_price}")
        st.write(f"Minimum Price: {min_price}")
        st.write(f"Average Price: {average_price:.2f} лв.")
        st.write(f"Median Price: {median_price:.2f} лв.")
    else:
        st.warning("No data available to calculate aggregated values.")
