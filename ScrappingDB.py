import os
import time
import signal
import sqlite3
import requests
import schedule
import pygetwindow as gw
import pyautogui
import html as ihtml
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tkinter as tk
from tkinter import messagebox
from datetime import date

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver():
    options = Options()
    # options.add_argument("--headless")  # Uncomment to run in background
    options.add_argument("--no-sandbox")
    options.add_argument('--start-maximized')
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

def bring_chrome_to_front():
    time.sleep(3)  # Wait for the Chrome window to be ready
    for window in gw.getWindowsWithTitle('Chrome'):
        try:
            if window.isMinimized:
                window.restore()
            window.activate()
            break
        except Exception as e:
            print("⚠️ Could not bring Chrome to front:", e)

def save_data_to_db(shopname, itemlink, productId):
    conn = sqlite3.connect('mydata.db')    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM linklist WHERE productid = ? and shopname =?', (productId,shopname,))
    rows = cursor.fetchall()
    if len(rows) == 0:
        cursor.execute('INSERT INTO linklist (shopname, productid , itemlink , status , emailstatus ) VALUES (? , ? , ?, ? , ?)', (shopname,productId, itemlink, '0' , '0'))
        conn.commit()
    conn.close()
    
def getProductId(html_string, shopname):
    
    if (shopname == 'grailed'):
        match = re.search(r'/listings/(\d+)', html_string)
        if match:
            return match.group(1)
        return None
    if (shopname == 'offerup'):
        match = re.search(r'/item/detail/([^/?]+)', html_string)
        if match:
            return match.group(1)
        return None

def scrape_ebay():
    url = "https://www.ebay.com/sch/i.html?_nkw=robin+jean&_sacat=0&_from=R40&_sop=10"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select(".s-item__info")
    results = []
    
    for item in items:
        title = item.select_one(".s-item__title")
        link = item.select_one("a")
        if title and link:
            results.append((title.text.strip(), link["href"], link["href"].split("/itm/")[1].split("?")[0]))
    return results[:20]

def scrape_mercari(driver):
    url = "https://www.mercari.com/search/?keyword=robin%20jean&sortBy=2"
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("a[data-testid='ProductThumbWrapper']")
    return [(item.text.strip(), "https://www.mercari.com" + item["href"],  item["href"].split('/')[3]) for item in items[:20]]

def scrape_grailed(driver):
    url = "https://www.grailed.com/shop/UjePVqGLHg"
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("a[href*='/listings/']")
    return [(item.text.strip(), "https://www.grailed.com" + item["href"],getProductId(item["href"],"grailed")) for item in items[:20]]

def scrape_offerup(driver):
    url = "https://offerup.com/search?q=robin%27s+jean&sort=recent&SORT=best_match&CONDITION=NEW"
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("a[href^='/item/']")
    return [(item.text.strip(), "https://offerup.com" + item["href"], getProductId(item["href"], 'offerup')) for item in items[:20]]

def scrape_poshmark(driver):
    url = "https://poshmark.com/search?query=robin%20jean&sort_by=added_desc"
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("a.tile__title")
    return [(item.text.strip(), "https://poshmark.com" + item["href"], item["data-et-prop-listing_id"]) for item in items[:20]]

def send_email_with_new_links():   
    webhook_url = "https://discord.com/api/webhooks/1363226528556777557/Jx0ctwnQvb1xjYsI847s6iiYlMp4BEcUcNYoNJX-LCXKMb90jEni5p6Vqff-cw3lApWA"
    conn = sqlite3.connect('mydata.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, itemlink FROM linklist WHERE status = '0' AND emailstatus = '0'")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return
    try:
        for id, itemlink in rows:
            data = {
                "content": itemlink
            }
            response = requests.post(webhook_url, json=data)
            # Check the response
            if response.status_code == 204:
                # Update emailstatus = 1
                ids_to_update = [str(row[0]) for row in rows]
                cursor.execute("UPDATE linklist SET emailstatus = '1' WHERE id = ?", (id,))
            conn.commit()

    except Exception as e:
        print("❌ Failed to send email:", e)
    finally:
        conn.close()

def main():
    driver = setup_driver()
    bring_chrome_to_front()  # 👈 Bring browser window to front
    print("\n================= 🛍 ROBIN'S JEAN LISTINGS =================\n")

    try:
        try:
            send_email_with_new_links()
        except Exception as e:
            print("❌ Send mail failed:", e)
            
        print("🛒 eBay:")
        for title, link, productId in scrape_ebay():
            save_data_to_db('eBay', link, productId)

        print("\n🧢 Mercari:")
        try:
            for title, link, productid in scrape_mercari(driver):
                save_data_to_db('Mercari', link, productid)
        except Exception as e:
            print("❌ Mercari scrape failed:", e)

        print("\n🧥 Grailed:")
        try:
            for title, link,productid in scrape_grailed(driver):
                save_data_to_db('Grailed', link,productid)
        except Exception as e:
            print("❌ Grailed scrape failed:", e)

        print("\n📱 OfferUp:")
        try:
            for title, link,productid in scrape_offerup(driver):
                save_data_to_db('OfferUp', link,productid)
        except Exception as e:
            print("❌ OfferUp scrape failed:", e)

        print("\n👗 Poshmark:")
        try:
            for title, link ,productid in scrape_poshmark(driver):
                save_data_to_db('Poshmark', link,productid)
        except Exception as e:
            print("❌ Poshmark scrape failed:", e)

        print("\n============================================================\n")

    finally:
        print("🔒 Closing Chrome...")
        driver.quit()

def job():
    print(f"⏰ Running job at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    main()
    

if __name__ == "__main__":    
    conn = sqlite3.connect('mydata.db')    
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS linklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shopname TEXT,
            productid TEXT,
            itemlink TEXT,
            status TEXT ,
            emailstatus TEXT 
        )
    ''')
    conn.commit()
    conn.close()

    schedule.every(1).minutes.do(job)

    # Run once at startup
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)
