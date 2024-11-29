import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import matplotlib.pyplot as plt
import re
from io import BytesIO

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

# Function to extract individual listing data
def extract_individual_data(url, headers):
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

# Streamlit app starts here
st.title("Car Listings Scraper")

# User input for base URL
base_url = st.text_input("Enter the base URL for scraping:", value="https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
headers = {'User-Agent': 'Mozilla/5.0'}

# Scrape data when the button is clicked
if st.button("Scrape Data"):
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
                
                # Extract individual data
                probeg, skorosti, dvigatel, moshtnost, year = extract_individual_data("https:" + title['href'], headers)
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

    # Display table of data
    st.subheader("Scraped Data")
    st.dataframe(df)

    # Provide download options
    csv = df.to_csv(index=False).encode('utf-8-sig')
    excel = BytesIO()
    df.to_excel(excel, index=False, sheet_name="Listings")
    excel.seek(0)

    st.download_button("Download as CSV", data=csv, file_name="listings.csv", mime="text/csv")
    st.download_button("Download as Excel", data=excel, file_name="listings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Aggregated data
    max_price = max(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
    min_price = min(prices_list, key=lambda x: float(x.replace(' лв.', '').replace(',', '')))
    max_price_link = df[df["Price (лв.)"] == max_price]["Link"].values[0]
    min_price_link = df[df["Price (лв.)"] == min_price]["Link"].values[0]

    st.subheader("Aggregated Data")
    st.write(f"Total Listings: {len(prices_list)}")
    st.write(f"Maximum Price: {max_price} (Link: [View Listing]({max_price_link}))")
    st.write(f"Minimum Price: {min_price} (Link: [View Listing]({min_price_link}))")
    average_price = statistics.mean([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
    median_price = statistics.median([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list])
    st.write(f"Average Price: {average_price:.2f} лв.")
    st.write(f"Median Price: {median_price:.2f} лв.")

    # Visualization
    st.subheader("Visualizations")
    st.write("### Price Distribution")
    fig, ax = plt.subplots()
    ax.hist([float(p.replace(' лв.', '').replace(',', '')) for p in prices_list], bins=20, edgecolor='black')
    ax.set_title("Price Distribution")
    ax.set_xlabel("Price (лв.)")
    ax.set_ylabel("Frequency")
    st.pyplot(fig)
