
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Function to extract price
def extract_price(price_div):
    match = re.search(r'(\d+[\s,]?\d*)\s*(лв|EUR|€|USD|\$)', price_div)
    if match:
        return match.group(1).replace(" ", "").replace(",", "")
    return None

# Streamlit app
st.title("Mobile.bg Web Scraper")

# User input for base URL
base_url = st.text_input("Enter the base URL to scrape:", "https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
headers = {'User-Agent': 'Mozilla/5.0'}

if st.button("Start Scraping"):
    try:
        # Prepare empty lists for data
        titles_list, prices_list, links_list = [], [], []

        # Fetch the webpage
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data
        ads = soup.find_all('div', class_='mobile-ads')
        for ad in ads:
            title = ad.find('a', class_='title').get_text(strip=True)
            price_div = ad.find('div', class_='price').get_text(strip=True)
            price = extract_price(price_div)
            link = ad.find('a', class_='title')['href']

            # Append data to lists
            titles_list.append(title)
            prices_list.append(price)
            links_list.append(link)

        # Create a DataFrame
        data = pd.DataFrame({
            'Title': titles_list,
            'Price': prices_list,
            'Link': links_list
        })

        # Display the DataFrame
        st.dataframe(data)

        # Option to download data as CSV
        csv = data.to_csv(index=False)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="scraped_data.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
