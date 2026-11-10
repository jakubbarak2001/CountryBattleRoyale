from playwright.sync_api import sync_playwright
from unittest import TestCase

class TestGame(TestCase):
    def test_one_round(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page()
            page.goto("http://127.0.0.1:5000/")
            first_round_country_name = page.locator("#country-01").inner_text()

            country_button_locator = page.locator("button.country-choice:nth-child(1)")
            country_button_locator.click()

            second_round_button_locator = page.locator(".new-matchup-button--next")
            second_round_button_locator.click()
            second_round_country_name = page.locator("#country-01").inner_text()

            browser.close()
            self.assertNotEqual(first_round_country_name, second_round_country_name)