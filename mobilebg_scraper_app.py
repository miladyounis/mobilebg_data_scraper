import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import statistics
import plotly.express as px

st.set_page_config(page_title="Car Dashboard", layout="wide")

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

def extract_individual_data(url, headers):
    response = requests.get(url, headers=headers)
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
    headers = {'User-Agent': 'Mozilla/5.0'}
    page = 1
    titles, prices, links, probegs, transmissions, engines, powers, years = [], [], [], [], [], [], [], []

    while True:
        url = f"{base_url}/p-{page}" if page > 1 else base_url
        response = requests.get(url, headers=headers)
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

                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'], headers)
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
        bargap=0.1
    )
    st.plotly_chart(fig_price_dist, use_container_width=True)

        # Transmission Type Count (Interactive Pie Chart)
    st.write("### Number of Listings by Transmission Type")
    transmission_counts = df['Transmission'].value_counts().reset_index()
    transmission_counts.columns = ['Transmission', 'Count']
    fig_transmission = px.pie(
        transmission_counts,
        names="Transmission",
        values="Count",
        hole=0.4,
        color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    )
    fig_transmission.update_traces(
        textposition="outside",  # Place labels and percentages outside the pie
        textinfo="label+percent",  # Display both label and percentage
        pull=[0.05] * len(transmission_counts)  # Slightly pull out all segments for better spacing
    )
    fig_transmission.update_layout(
        showlegend=False,  # Disable the separate legend
        title=None
    )
    st.plotly_chart(fig_transmission, use_container_width=True)

    st.write("### Number of Listings by Engine Type")
    engine_counts = df['Engine'].value_counts().reset_index()
    engine_counts.columns = ['Engine', 'Count']
    fig_engine = px.bar(
        engine_counts,
        x="Engine",
        y="Count",
        labels={"Engine": "Engine Type", "Count": "Count"},
        color_discrete_sequence=["#EF553B"]
    )
    fig_engine.update_layout(
        xaxis_title="Engine Type",
        yaxis_title="Count",
    )
    st.plotly_chart(fig_engine, use_container_width=True)

    st.write("### Price vs Mileage Scatter Plot")
    valid_mileage = df.dropna(subset=["Mileage"])
    valid_mileage["Mileage"] = valid_mileage["Mileage"].str.replace(r"[^\d.]", "", regex=True).astype(float)
    valid_mileage = valid_mileage.sort_values(by="Mileage")
    fig_scatter = px.scatter(
        valid_mileage,
        x="Mileage",
        y="Price",
        labels={"Mileage": "Mileage (km)", "Price": "Price (лв.)"},
        color_discrete_sequence=["#00CC96"]
    )
    fig_scatter.update_layout(
        xaxis_title="Mileage (km)",
        yaxis_title="Price (лв.)",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.write("### Number of Cars per Year")
    year_counts = df['Year'].value_counts().reset_index()
    year_counts.columns = ['Year', 'Count']
    year_counts = year_counts.sort_values(by="Year")
    fig_year = px.bar(
        year_counts,
        x="Year",
        y="Count",
        labels={"Year": "Year", "Count": "Count"},
        color_discrete_sequence=["#AB63FA"]
    )
    fig_year.update_layout(
        xaxis_title="Year",
        yaxis_title="Count",
    )
    st.plotly_chart(fig_year, use_container_width=True)

    # Data Overview at the bottom
    st.write("### Data Overview")
    df_sorted = df.sort_values(by="Price", ascending=True)
    st.dataframe(df, use_container_width=True)
