import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Define functions
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

def extract_individual_data(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    data = {
        "titles_list": soup.find('h1').get_text(strip=True),
        "probeg_list": soup.find(text=re.compile("Пробег")).parent.parent.find('td').get_text(strip=True),
        "skorosti_list": soup.find(text=re.compile("Скорости")).parent.parent.find('td').get_text(strip=True),
        "dvigatel_list": soup.find(text=re.compile("Двигател")).parent.parent.find('td').get_text(strip=True),
        "moshtnost_list": soup.find(text=re.compile("Мощност")).parent.parent.find('td').get_text(strip=True),
        "year_list": soup.find(text=re.compile("Година")).parent.parent.find('td').get_text(strip=True),
    }
    return data

# Streamlit interface
st.title("Mobile.bg Web Scraper")

# Input
base_url = st.text_input("Enter the Base URL:", placeholder="https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
headers = {'User-Agent': 'Mozilla/5.0'}

if st.button("Start Scraping"):
    if not base_url:
        st.error("Please provide a valid URL.")
    else:
        try:
            response = requests.get(base_url, headers=headers)
            soup = BeautifulSoup(response.content, "html.parser")
            
            titles_list, prices_list, links_list = [], [], []
            
            for listing in soup.find_all('div', class_='listing-item'):
                title = listing.find('a').get_text(strip=True)
                link = listing.find('a')['href']
                price_div = listing.find('div', class_='price').get_text(strip=True)
                
                titles_list.append(title)
                prices_list.append(extract_price(price_div))
                links_list.append(link)
            
            # Display results
            results = pd.DataFrame({
                "Title": titles_list,
                "Price": prices_list,
                "Link": links_list,
            })
            st.dataframe(results)
            
            # Downloadable file
            csv = results.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="scraped_data.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")
