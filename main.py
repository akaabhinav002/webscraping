import streamlit as st
import subprocess
import sys
import os

# Streamlit app
st.title("Recording Studio Scraper")

location = st.text_input("Location (e.g., Dublin, Mumbai, Paris):")
total_results = st.number_input("Number of results to scrape:", min_value=1, step=1)

def run_scraping():
    if location and total_results:
        # Call the separate script with arguments
        subprocess.run([sys.executable, "scraper.py", "-l", location, "-t", str(total_results)])
        st.success(f"Scraping started! Check below for the results once completed.")

        # Provide download links for the output files
        output_dir = 'output'
        if os.path.exists(output_dir):
            for file_name in os.listdir(output_dir):
                file_path = os.path.join(output_dir, file_name)
                if file_name.endswith('.csv') or file_name.endswith('.xlsx'):
                    st.download_button(
                        label=f"Download {file_name}",
                        data=open(file_path, "rb"),
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
    else:
        st.error("Please provide both location and total number of results.")

if st.button("Start Scraping"):
    run_scraping()
