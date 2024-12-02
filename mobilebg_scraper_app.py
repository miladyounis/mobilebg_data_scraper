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

        st.write("### Filters")
        filter_row1 = st.columns(3)
        with filter_row1[0]:
            transmission_filter = st.selectbox("Transmission Type", options=["All"] + list(df['Transmission'].dropna().unique()))
        with filter_row1[1]:
            year_filter = st.selectbox("Year", options=["All"] + sorted(df['Year'].dropna().unique()))
        with filter_row1[2]:
            engine_filter = st.selectbox("Engine Type", options=["All"] + list(df['Engine'].dropna().unique()))

        filter_row2 = st.columns(2)
        with filter_row2[0]:
            price_range = st.slider(
                "Price Range (лв.)", 
                min_value=int(df['Price'].min()), 
                max_value=int(df['Price'].max()), 
                value=(int(df['Price'].min()), int(df['Price'].max()))
            )
        with filter_row2[1]:
            mileage_max = int(df['Mileage'].dropna().str.replace(r"[^\d.]", "", regex=True).astype(float).max())
            mileage_range = st.slider("Mileage Range (km)", min_value=0, max_value=mileage_max, value=(0, mileage_max))

        filtered_df = df[
            ((df['Transmission'] == transmission_filter) | (transmission_filter == "All")) &
            ((df['Year'] == year_filter) | (year_filter == "All")) &
            ((df['Engine'] == engine_filter) | (engine_filter == "All")) &
            (df['Price'].between(price_range[0], price_range[1])) &
            (df['Mileage'].str.replace(r"[^\d.]", "", regex=True).astype(float).between(mileage_range[0], mileage_range[1]))
        ]

        if filtered_df.empty:
            st.warning("No results found. Adjust your filters.")
        else:
            st.write("### Price Distribution")
            fig_price_dist = px.histogram(
                filtered_df,
                x="Price",
                nbins=20,
                labels={"Price": "Price (лв.)"}
            )
            st.plotly_chart(fig_price_dist, use_container_width=True)

            st.write("### Listings Breakdown")
            chart_row1 = st.columns([1, 1, 1])

            transmission_counts = filtered_df['Transmission'].value_counts().reset_index()
            transmission_counts.columns = ['Transmission', 'Count']
            fig_transmission = px.pie(
                transmission_counts,
                names="Transmission",
                values="Count",
                hole=0.4
            )
            chart_row1[0].plotly_chart(fig_transmission, use_container_width=True)

            engine_counts = filtered_df['Engine'].value_counts().reset_index()
            engine_counts.columns = ['Engine', 'Count']
            fig_engine = px.bar(
                engine_counts,
                y="Engine",
                x="Count",
                orientation="h"
            )
            chart_row1[1].plotly_chart(fig_engine, use_container_width=True)

            year_counts = filtered_df['Year'].value_counts().reset_index()
            year_counts.columns = ['Year', 'Count']
            year_counts = year_counts.sort_values(by="Year")
            fig_year = px.bar(
                year_counts,
                y="Year",
                x="Count",
                orientation="h"
            )
            chart_row1[2].plotly_chart(fig_year, use_container_width=True)

            st.write("### Price vs Mileage Scatter Plot")
            valid_mileage = filtered_df.dropna(subset=["Mileage"])
            valid_mileage["Mileage"] = valid_mileage["Mileage"].str.replace(r"[^\d.]", "", regex=True).astype(float)
            fig_scatter = px.scatter(
                valid_mileage,
                x="Mileage",
                y="Price",
                labels={"Mileage": "Mileage (km)", "Price": "Price (лв.)"}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            st.write("### Data Overview")
            st.dataframe(filtered_df, use_container_width=True)

            st.download_button("Download Data as CSV", filtered_df.to_csv(index=False), "filtered_data.csv")
