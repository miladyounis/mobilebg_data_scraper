import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import statistics
import plotly.express as px
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

st.set_page_config(page_title="Car Dashboard", layout="wide")

# Enhanced request session with retry logic
def create_request_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # Retry up to 3 times
        backoff_factor=1,  # Wait progressively longer between retries
        status_forcelist=[429, 500, 502, 503, 504]  # Retry on these status codes
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Base scraping and processing functions
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

def extract_individual_data(url, session):
    response = session.get(url)
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

def scrape_data(base_url):
    session = create_request_session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    session.headers.update(headers)

    page = 1
    titles, prices, links, probegs, transmissions, engines, powers, years = [], [], [], [], [], [], [], []

    while True:
        url = f"{base_url}/p-{page}" if page > 1 else base_url
        response = session.get(url)
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

                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'], session)
                probegs.append(probeg)
                transmissions.append(skorosti)
                engines.append(dvigatel)
                powers.append(moshtnost)
                years.append(year)

        page += 1

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

# Streamlit UI
st.title("Car Listings Dashboard")
base_url = st.text_input("Enter the base URL for scraping:", "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc40")

if st.button("Scrape Data"):
    with st.spinner("Scraping data..."):
        df = scrape_data(base_url)

    # Gracefully handle empty data
    if df.empty:
        st.error("No data was found. Please check the URL or try again later.")
    else:
        # KPI Bar
        st.write("### Price Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Listings Found", f"{len(df)}")
        col2.metric("Maximum Price", f"{df['Price'].max():,.2f} лв.")
        col3.metric("Minimum Price", f"{df['Price'].min():,.2f} лв.")
        col4.metric("Average Price", f"{df['Price'].mean():,.2f} лв.")
        col5.metric("Median Price", f"{statistics.median(df['Price']):,.2f} лв.")

        # Visualizations
        st.write("### Price Distribution")
        fig_price_dist = px.histogram(
            df,
            x="Price",
            nbins=20,
            labels={"Price": "Price (лв.)"},
            color_discrete_sequence=["#0070F2"]
        )
        fig_price_dist.update_layout(
            xaxis_title="Price (лв.)",
            yaxis_title="Frequency",
            title=None,
            bargap=0.1
        )
        st.plotly_chart(fig_price_dist, use_container_width=True)

        # Data Overview at the bottom
        st.write("### Data Overview")
        df_sorted = df.sort_values(by="Price", ascending=True)  # Sort by price ascending
        st.dataframe(df_sorted, use_container_width=True)
