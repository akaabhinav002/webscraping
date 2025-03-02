import argparse
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import os
import re

# Ensure Playwright browsers are installed
os.system("playwright install")

@dataclass
class Studio:
    """Holds studio data"""
    name: str = None
    website: str = "Not listed"
    phone_number: str = None
    email: str = None
    address: str = None
    prices: str = None
    services: str = None
    collaborations: str = None

@dataclass
class StudioList:
    """Holds list of Studio objects and saves data"""
    studios: list[Studio] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """Transforms studio list into a pandas DataFrame"""
        return pd.DataFrame([asdict(studio) for studio in self.studios])

    def save_to_excel(self, filename):
        """Saves pandas DataFrame to an Excel file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"{self.save_at}/{filename}.xlsx", index=False)
        print(f"Excel file created: {self.save_at}/{filename}.xlsx")

    def save_to_csv(self, filename):
        """Saves pandas DataFrame to a CSV file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"{self.save_at}/{filename}.csv", index=False, encoding="utf-8")
        print(f"CSV file created: {self.save_at}/{filename}.csv")

def clean_text(text):
    """Removes unwanted characters and fixes encoding issues"""
    return text.encode("utf-8", "ignore").decode("utf-8").strip() if text else None

def extract_studio_details(context, studio):
    """Scrape additional details from the studio's website"""
    if studio.website and studio.website != "Not listed":
        try:
            page = context.new_page()
            page.goto(studio.website, timeout=90000)
            page.wait_for_timeout(8000)

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)

            page_content = page.content()

            # Extract email
            email_links = page.locator("xpath=//a[contains(@href, 'mailto:')]").all()
            if email_links:
                studio.email = clean_text(email_links[0].get_attribute("href").replace("mailto:", ""))
            else:
                email_match = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_content)
                studio.email = email_match[0] if email_match else None

            # Extract prices
            price_match = re.findall(r"(?:€|£|₹|\$)\s?\d{1,4}(?:\.\d{1,2})?\s?(?:per|/)?\s?(?:hour|hr|session|day|month|week)?", page_content, re.IGNORECASE)
            studio.prices = ", ".join(set(price_match)) if price_match else None

            # Extract services
            services_match = re.findall(r"(mixing|mastering|recording|production|engineering|vocals|instrumental|editing|sound design)", page_content, re.IGNORECASE)
            studio.services = ", ".join(set(services_match)) if services_match else None

            # Extract clients/collaborations
            studio.collaborations = extract_clients(page)

            page.close()

        except Exception as e:
            print(f"Error extracting website data for {studio.name}: {e}")

def extract_clients(page):
    """Finds and extracts client names or links from the website."""
    try:
        possible_links = page.locator(
            "xpath=//a[contains(text(), 'Clients') or contains(text(), 'Our Clients') or contains(text(), 'Collaborations') or contains(text(), 'Work') or contains(text(), 'Our Gallery')]"
        )

        client_texts = []
        client_links = []

        if possible_links.count() > 0:
            base_url = page.url

            for link in possible_links.all():
                href = link.get_attribute("href")

                if href and href.startswith("/"):
                    href = base_url.rstrip("/") + href

                client_links.append(href)

                try:
                    page.goto(href, timeout=60000)
                    page.wait_for_timeout(5000)

                    text_elements = page.locator("//body//*[not(self::script) and not(self::style)]").all()
                    for element in text_elements:
                        text = clean_text(element.text_content())
                        if text and 3 < len(text) < 100:
                            client_texts.append(text)
                except Exception as e:
                    print(f"Skipping client link due to error: {e}")

        if client_links:
            return ", ".join(client_links)
        elif client_texts:
            return ", ".join(set(client_texts))
        else:
            return "No clients listed"

    except Exception as e:
        print(f"Error extracting clients: {e}")
        return "No clients listed"

def main(location, total_results):
    search_query = f"recording studios in {location}"
    print("Starting scraping...")
    print(f"Searching for: {search_query}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.google.com/maps", timeout=120000)  # Increased timeout
        page.wait_for_load_state("networkidle", timeout=120000)  # Wait for network to be idle
        print("Page loaded successfully")

        page.locator('//input[@id="searchboxinput"]').fill(search_query)
        page.keyboard.press("Enter")
        page.wait_for_timeout(15000)  # Increased timeout

        # Wait for results to load
        page.wait_for_selector("//div[contains(@aria-label, 'Results for')]", timeout=120000)  # Increased timeout
        print("Results loaded successfully")

        results_panel = page.locator("xpath=//div[contains(@aria-label, 'Results for')]")

        studio_list = StudioList()
        processed_urls = set()
        processed_count = 0
        batch_size = 3

        while processed_count < total_results:
            listings = page.locator("//a[contains(@href, 'https://www.google.com/maps/place')]").all()

            for i, listing in enumerate(listings):
                if processed_count >= total_results:
                    break

                href = listing.get_attribute("href", timeout=90000)  # Increased timeout
                if href in processed_urls:
                    continue

                try:
                    listing.click()
                    page.wait_for_timeout(7000)  # Increased timeout

                    studio = Studio()

                    h1_elements = page.locator("//h1").all()
                    studio.name = clean_text(h1_elements[-1].inner_text()) if h1_elements else None

                    address_element = page.locator("//button[@data-item-id='address']")
                    studio.address = clean_text(address_element.inner_text()) if address_element.count() > 0 else None

                    website_element = page.locator("xpath=//a[@data-item-id='authority']")
                    studio.website = website_element.get_attribute("href") if website_element.count() > 0 else "Not listed"

                    phone_element = page.locator("xpath=//a[contains(@href, 'tel:')]")
                    studio.phone_number = clean_text(phone_element.get_attribute("href").replace("tel:", "")) if phone_element.count() > 0 else None

                    extract_studio_details(context, studio)

                    studio_list.studios.append(studio)
                    processed_urls.add(href)
                    processed_count += 1

                    page.go_back()
                    page.wait_for_timeout(7000)  # Increased timeout

                except Exception as e:
                    print(f"Error occurred: {e}")

                if (i + 1) % batch_size == 0:
                    results_panel.evaluate("(element) => element.scrollTop += 1000;")
                    page.wait_for_timeout(7000)  # Increased timeout

            new_listings = page.locator("//a[contains(@href, 'https://www.google.com/maps/place')]").all()
            if len(new_listings) == len(listings):
                more_places_button = page.locator("//button[contains(text(), 'More places')]")
                if more_places_button.count() > 0:
                    print("Clicking 'More places' button...")
                    more_places_button.click()
                    page.wait_for_timeout(15000)  # Increased timeout
                else:
                    print("No more results found.")
                    break

        print(f"Total Scraped: {len(studio_list.studios)}")

        filename = f"recording_studios_{location}".replace(' ', '_')
        studio_list.save_to_excel(filename)
        studio_list.save_to_csv(filename)

        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--location", type=str, required=True, help="Location (e.g., Dublin, Mumbai, Paris)")
    parser.add_argument("-t", "--total", type=int, required=True, help="Number of results to scrape")
    args = parser.parse_args()
    main(args.location, args.total)
