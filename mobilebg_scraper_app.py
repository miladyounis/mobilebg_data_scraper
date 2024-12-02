import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import statistics
import plotly.express as px
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

st.set_page_config(page_title="Car Dashboard", layout="wide")

@st.cache_data
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

@st.cache_data
def extract_individual_data(url, headers, session):
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.encoding = 'windows-1251'
        soup = BeautifulSoup(response.text, "html.parser")

        probeg = skorosti = dvigatel = moshtnost = year = None

        main_params = soup.find("div", class_="mainCarParams")
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
        if items:
            for item in items.find_all("div", class_="item"):
                if "Дата на производство" in item.text:
                    year_match = re.search(r"(\d{4})", item.text)
                    if year_match:
                        year = year_match.group(1)

        return probeg, skorosti, dvigatel, moshtnost, year
    except Exception as e:
        st.error(f"Error fetching individual data: {e}")
        return None, None, None, None, None

@st.cache_data
def scrape_data(base_url, max_pages=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    page = 1
    titles, prices, links, probegs, transmissions, engines, powers, years = [], [], [], [], [], [], [], []

    while page <= max_pages:
        try:
            url = f"{base_url}/p-{page}" if page > 1 else base_url
            response = session.get(url, headers=headers, timeout=10)
            response.encoding = 'windows-1251'
            soup = BeautifulSoup(response.text, "html.parser")

            titles_on_page = soup.find_all("a", class_="title")
            prices_on_page = soup.find_all("div", class_="price")

            if not titles_on_page:
                break

            for title, price_div in zip(titles_on_page, prices_on_page):
                processed_price = extract_price(price_div.text.strip())
                if processed_price:
                    titles.append(title.text.strip())
                    prices.append(processed_price)
                    links.append("https:" + title['href'])

                    probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'], headers, session)
                    probegs.append(probeg)
                    transmissions.append(skorosti)
                    engines.append(dvigatel)
                    powers.append(moshtnost)
                    years.append(year)

            page += 1
            time.sleep(random.uniform(1, 3))  # Simulate human behavior
        except Exception as e:
            st.error(f"Error scraping page {page}: {e}")
            break

    return pd.DataFrame({
        "Title": titles,
        "Price": prices,
        "Link": links,
        "Mileage": probegs,
        "Transmission": transmissions,
        "Engine": engines,
        "Power": powers,
        "Year": years,
    })

# Streamlit Interface
st.title("Car Listings Dashboard")
base_url = st.text_input("Enter the base URL for scraping:", "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc40")
max_pages = st.slider("Maximum Pages to Scrape", 1, 10, 3)

if st.button("Scrape Data"):
    with st.spinner("Scraping data..."):
        df = scrape_data(base_url, max_pages=max_pages)

    if df.empty:
        st.warning("No data found. Try a different URL or increase the page limit.")
    else:
        st.write("### Price Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Listings Found", f"{len(df)}")
        col2.metric("Maximum Price", f"{df['Price'].max():,.0f} лв.")
        col3.metric("Minimum Price", f"{df['Price'].min():,.0f} лв.")
        col4.metric("Average Price", f"{df['Price'].mean():,.0f} лв.")
        col5.metric("Median Price", f"{statistics.median(df['Price']):,.0f} лв.")

        st.write("### Data Overview")
        st.dataframe(df, use_container_width=True)

        st.download_button("Download Data as CSV", df.to_csv(index=False), "data.csv")
