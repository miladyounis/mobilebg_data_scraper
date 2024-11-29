import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

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

# Function to extract individual data
def extract_individual_data(url):
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(response.content, 'html.parser')
    details = soup.find_all("div", {"class": "some-detail-class"})  # Adjust the class as per requirement
    # Add your data extraction logic here
    return details

# Main Streamlit app
def main():
    st.title("Mobile Scraping App")
    st.write("Enter the base URL of the mobile.bg site to scrape data.")
    
    # User input for the base URL
    base_url = st.text_input("Base URL", value="https://www.mobile.bg/obiavi/avtomobili-dzhipove/volvo/xc60")
    
    if st.button("Start Scraping"):
        if not base_url:
            st.error("Please enter a valid URL.")
        else:
            try:
                # Placeholder: Call scraping functions and display results
                response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(response.content, 'html.parser')
                
                titles = [item.text for item in soup.find_all("h2", {"class": "title-class"})]  # Adjust selectors
                prices = [extract_price(item.text) for item in soup.find_all("div", {"class": "price-class"})]
                
                data = pd.DataFrame({"Title": titles, "Price": prices})
                st.write(data)
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
