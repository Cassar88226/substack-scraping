from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import re
import argparse
import os
from urllib.parse import urlparse

def get_options():
    # Set up Chrome WebDriver with options
    options = webdriver.ChromeOptions()
    # Disable the first run dialog and other similar popups
    # options.add_argument("--headless")
    options.add_argument("--headless=new")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-gpu")
    return options

# Handle popups
def handle_popup(driver, xpath):
    try:
        button = driver.find_element(By.XPATH, xpath)
        button.click()
    except NoSuchElementException:
        print(f"Popup not found: {xpath}")

parser = argparse.ArgumentParser(description="Substack Scraping Application")
parser.add_argument('-u', '--username',  required=True, type=str, help="Input User Email")
parser.add_argument('-p', '--password', required=True, type=str, help="Input Password")
parser.add_argument('-s', '--substack', required=True, type=str, help="Input Substack Site Url")
args = parser.parse_args()

def main(substack, user_email, user_pwd):
    domain_name = urlparse(substack).netloc
    if not os.path.exists(domain_name):
        os.makedirs(domain_name)

    options = get_options()
    driver = webdriver.Chrome(options=options)

    # Navigate to the target website
    driver.get("{}".format(substack))
    time.sleep(2)

    # Define the XPaths for the popups
    popup_xpaths = [
        '/html/body/div/div[1]/div[2]/div[5]/div/div/div/a/button',
        '/html/body/div/div[1]/div[2]/div[3]/div[2]/div[2]/button'
    ]

    for xpath in popup_xpaths:
        handle_popup(driver, xpath)
        time.sleep(2)

    # Click on the Sign In button using the exact class attribute from the screenshot
    try:
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/div[1]/div[1]/div/div[1]/div[2]/div/button[3]'))
        )
        button.click()
    except (NoSuchElementException, TimeoutException):
        print("Sign In button not found or not clickable")
    time.sleep(2)

    # Click on the "Sign in with password" button
    try:
        
        button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="substack-login"]/div[2]/div[2]/form/div[2]/div')))
        button.click()
    except (NoSuchElementException, TimeoutException):
        print("Sign in with password not found or not clickable")
    time.sleep(2)

    # Enter email and password
    try:
        email = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, '//*[@id="substack-login"]/div[2]/div[2]/form/div[1]/input')))
        email.send_keys(user_email)
    except (NoSuchElementException, TimeoutException):
        print("Email input not found")
    time.sleep(0.5)

    try:
        password = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, '//*[@id="substack-login"]/div[2]/div[2]/form/input[3]')))
        password.send_keys(user_pwd)
    except (NoSuchElementException, TimeoutException):
        print("Password input not found")
    time.sleep(5)

    try:
        continue_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="substack-login"]/div[2]/div[2]/form/button[@class="button primary"]')))
        continue_button.click()
    except (NoSuchElementException, TimeoutException):
        print("Continue button not found")
    time.sleep(5)

    driver.get("{}".format(substack))
    time.sleep(2)

    high_element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div[2]/div/div/div/div[2]')))

    reached_page_end = False
    last_height = driver.execute_script("return document.body.scrollHeight")

    while not reached_page_end:
        element = driver.find_element(By.XPATH, '/html/body')
        element.send_keys(Keys.END)
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if last_height == new_height:
            reached_page_end = True
        else:
            last_height = new_height
    # Extract links to individual posts
    parent_element = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div/div/div[2]')
    link_elements = parent_element.find_elements(By.CSS_SELECTOR, '[data-testid="post-preview-title"]')

    href = [link.get_attribute("href") for link in link_elements]
    print(len(href))

    # Loop through the extracted links
    for i, url in enumerate(href, start=1):
        driver.get(url)
        time.sleep(4)
        element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div[2]')))
        # Extract inner HTML content
        try:
            element = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]')
            inner_html = element.get_attribute("innerHTML")
            # Use regular expressions to clean up inner HTML content
            patterns = [
                r'<div inert="" role="dialog".*?Other</div></button></div></div></div></div></div></div></div></div>',
                r'<div class="pencraft frontend-pencraft-Box-module__reset.*?frontend-pencraft-Box-module__padding-bottom-16--KVxKv"><div class="pencraft frontend-pencraft-Box-module__reset.*?</circle></svg></a></div></div></div>',
                r'<div class="pencraft frontend-pencraft-Box-module__reset--VfQY8 frontend-pencraft-Box-module__display-flex.*?</line></svg></a></div></div></div></div></div>',
                r'<div class="like-button-container post-ufi-button style-compressed"><a role="button" class="post-ufi-button style-compressed.*?</div></button></div></div></div></div></div></div></div></div>'
            ]

            for pattern in patterns:
                inner_html = re.sub(pattern, '', inner_html, flags=re.DOTALL)

            try:
                element = driver.find_element(By.CSS_SELECTOR, ".post-title.unpublished")
                filename = re.sub(r'[^\w\s-]', '', element.text)
            except NoSuchElementException:
                try:
                    element = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div[1]/div/article/div[3]/div[2]/div[1]/div/div[1]/div/div/div[1]/h2')
                    filename = re.sub(r'[^\w\s-]', '', element.text)
                except:
                    element = driver.find_element(By.CSS_SELECTOR, ".tw-mt-0.tw-mb-2.tw-leading-tight.sm\\:tw-mb-1.tw-text-3xl.sm\\:tw-text-3xl")
                    filename = re.sub(r'[^\w\s-]', '', element.text)

            with open(os.path.join(domain_name, f'{i} {filename}.html'), 'w', encoding='utf-8') as file:
                file.write(inner_html)
        except NoSuchElementException as e:
            element = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]')
            inner_html = element.get_attribute("innerHTML")
            with open(os.path.join(domain_name, f'{i}.html'), 'w', encoding='utf-8') as file:
                file.write(inner_html)
            print(e)
            print("No title found or content extraction failed")
        except TimeoutException as e:
            print("timeout exception", i)

    # Uncomment this line to close the WebDriver
    driver.quit()

if __name__ == "__main__":
    user_email = args.username
    user_pwd = args.password
    substack = args.substack
    
    main(substack, user_email, user_pwd)