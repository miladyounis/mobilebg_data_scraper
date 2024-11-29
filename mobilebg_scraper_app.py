
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("Mobile.bg Scraper")

# Allow the user to input the base URL
base_url = st.text_input("Enter the base URL for scraping:", "")
if not base_url:
    st.warning("Please enter a valid base URL.")
    st.stop()

headers = {'User-Agent': 'Mozilla/5.0'}

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

# Scrape data
st.write("Scraping data...")
try:
    response = requests.get(base_url, headers=headers)
    response.encoding = 'windows-1251'
    soup = BeautifulSoup(response.text, "html.parser")

    titles = soup.find_all("a", class_="title")
    prices = soup.find_all("div", class_="price")

    for title, price in zip(titles, prices):
        price_text = price.text.strip()
        processed_price = extract_price(price_text)
        if processed_price:
            titles_list.append(title.text.strip())
            prices_list.append(processed_price)
            links_list.append("https:" + title['href'])

    if not titles_list:
        st.error("No data available for the given base URL.")
        st.stop()

    # Create DataFrame
    df = pd.DataFrame({
        "Title": titles_list,
        "Price (лв.)": prices_list,
        "Link": links_list,
    })
    st.write("### Scraped Data")
    st.dataframe(df)

    # Save DataFrame to CSV
    filename = f"scraped_listings.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    st.success(f"Data saved to {filename}")

except Exception as e:
    st.error(f"An error occurred: {e}")
