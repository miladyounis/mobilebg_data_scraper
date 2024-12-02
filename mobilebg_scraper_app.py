import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import statistics
import plotly.express as px
import re

st.set_page_config(page_title="Car Dashboard", layout="wide")

# Selenium setup with headless browser
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Scraping function using Selenium
def scrape_data(base_url):
    driver = setup_selenium()
    driver.get(base_url)
    
    titles, prices, links, probegs, transmissions, engines, powers, years = [], [], [], [], [], [], [], []
    
    while True:
        car_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
        price_elements = driver.find_elements(By.CSS_SELECTOR, "div.price")
        
        if not car_elements:
            break

        for car, price_element in zip(car_elements, price_elements):
            title = car.text.strip()
            price_text = price_element.text.strip()
            price_match = re.search(r"(\d+[\s,]?\d*)\s*(лв\.|EUR)", price_text)
            
            if price_match:
                price = float(price_match.group(1).replace(",", "").replace(" ", ""))
                if price_match.group(2) == "EUR":
                    price *= 1.95  # Convert EUR to BGN

                titles.append(title)
                prices.append(price)
                links.append(car.get_attribute("href"))

        try:
            next_page = driver.find_element(By.CSS_SELECTOR, "a.next")
            next_page.click()
        except Exception:
            break

    driver.quit()

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

        # Price Distribution
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

        # Number of Listings by Transmission Type
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
            textposition="outside",
            textinfo="label+percent",
            pull=[0.05] * len(transmission_counts)
        )
        fig_transmission.update_layout(
            showlegend=False,
            title=None
        )
        st.plotly_chart(fig_transmission, use_container_width=True)

        # Number of Listings by Engine Type
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
            title=None
        )
        st.plotly_chart(fig_engine, use_container_width=True)

        # Price vs Mileage Scatter Plot
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
            title=None
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Number of Cars per Year
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
            title=None
        )
        st.plotly_chart(fig_year, use_container_width=True)

        # Data Overview at the bottom
        st.write("### Data Overview")
        df_sorted = df.sort_values(by="Price", ascending=True)
        st.dataframe(df_sorted, use_container_width=True)
