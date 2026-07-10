import pandas as pd
import numpy as np
from faker import Faker
import random
import os

# Initialize Faker with multiple locales
locales = ['en_US', 'es_ES', 'fr_FR', 'de_DE', 'hi_IN', 'zh_CN']
fake = Faker(locales)

Faker.seed(42)
np.random.seed(42)
random.seed(42)

def make_10_digit_phone():
    return f"{random.randint(2,9)}{random.randint(100,999)}{random.randint(1000,9999)}"

def generate_multilingual_customers(num_records=500):
    data = []
    
    # Generate Base Records (English)
    base_records = []
    for _ in range(num_records):
        record = {
            'CustomerID': fake['en_US'].unique.uuid4()[:8],
            'FullName': fake['en_US'].name(),
            'Email': fake['en_US'].email(),
            'Phone': make_10_digit_phone(),
            'Address': fake['en_US'].street_address(),
            'City': fake['en_US'].city(),
            'Country': 'United States',
            'Language': 'English'
        }
        base_records.append(record)
    
    # Add them to data
    data.extend(base_records)
    
    # Introduce Multilingual Duplicates
    # We will pick 10% of the base records and create duplicates in different languages.
    # The duplicate will have the SAME CustomerID and Phone (to act as deduplication keys), 
    # but the Name and Address will be generated in a different locale.
    
    num_duplicates = int(num_records * 0.15)
    records_to_duplicate = random.sample(base_records, num_duplicates)
    
    for record in records_to_duplicate:
        # Pick a random non-English locale
        target_locale = random.choice(['es_ES', 'fr_FR', 'de_DE', 'hi_IN', 'zh_CN'])
        
        lang_map = {
            'es_ES': 'Spanish',
            'fr_FR': 'French',
            'de_DE': 'German',
            'hi_IN': 'Hindi',
            'zh_CN': 'Chinese'
        }
        country_map = {
            'es_ES': 'Spain',
            'fr_FR': 'France',
            'de_DE': 'Germany',
            'hi_IN': 'India',
            'zh_CN': 'China'
        }
        
        dup_record = {
            'CustomerID': record['CustomerID'], # SAME ID
            'FullName': fake[target_locale].name(), # Localized Name
            'Email': record['Email'], # Same Email (or could be localized, let's keep it same for easier linking but different name)
            'Phone': record['Phone'], # SAME Phone
            'Address': fake[target_locale].street_address(), # Localized Address
            'City': fake[target_locale].city(),
            'Country': country_map[target_locale],
            'Language': lang_map[target_locale]
        }
        data.append(dup_record)
        
    df = pd.DataFrame(data)
    
    # Introduce regular missing values randomly
    for col in ['FullName', 'Email', 'Address', 'City']:
        mask = np.random.rand(len(df)) < 0.05
        df.loc[mask, col] = np.nan
        
    # Shuffle
    df = df.sample(frac=1).reset_index(drop=True)
    
    df.to_csv('multilingual_global_customers.csv', index=False, encoding='utf-8-sig')
    print("Created multilingual_global_customers.csv")

def generate_multilingual_products():
    # Hardcoded translations for true semantic duplication testing
    products_catalog = [
        {"id": "P001", "price": 25.99, "en": "Wireless Mouse", "es": "Ratón inalámbrico", "fr": "Souris sans fil", "de": "Kabellose Maus", "hi": "वायरलेस माउस", "zh": "无线鼠标"},
        {"id": "P002", "price": 89.50, "en": "Gaming Keyboard", "es": "Teclado para juegos", "fr": "Clavier de jeu", "de": "Gaming-Tastatur", "hi": "गेमिंग कीबोर्ड", "zh": "游戏键盘"},
        {"id": "P003", "price": 45.00, "en": "Bluetooth Headphones", "es": "Auriculares Bluetooth", "fr": "Écouteurs Bluetooth", "de": "Bluetooth-Kopfhörer", "hi": "ब्लूटूथ हेडफ़ोन", "zh": "蓝牙耳机"},
        {"id": "P004", "price": 19.99, "en": "Laptop Stand", "es": "Soporte para portátil", "fr": "Support pour ordinateur portable", "de": "Laptoptänder", "hi": "लैपटॉप स्टैंड", "zh": "笔记本电脑支架"},
        {"id": "P005", "price": 199.99, "en": "Smart Watch", "es": "Reloj inteligente", "fr": "Montre intelligente", "de": "Smartwatch", "hi": "स्मार्ट वॉच", "zh": "智能手表"},
        {"id": "P006", "price": 12.50, "en": "USB-C Cable", "es": "Cable USB-C", "fr": "Câble USB-C", "de": "USB-C-Kabel", "hi": "USB-C केबल", "zh": "USB-C 数据线"},
        {"id": "P007", "price": 299.00, "en": "Office Chair", "es": "Silla de oficina", "fr": "Chaise de bureau", "de": "Bürostuhl", "hi": "कार्यालय की कुर्सी", "zh": "办公椅"},
        {"id": "P008", "price": 150.00, "en": "Mechanical Keyboard", "es": "Teclado mecánico", "fr": "Clavier mécanique", "de": "Mechanische Tastatur", "hi": "मैकेनिकल कीबोर्ड", "zh": "机械键盘"},
        {"id": "P009", "price": 55.00, "en": "Webcam 1080p", "es": "Cámara web 1080p", "fr": "Webcam 1080p", "de": "Webcam 1080p", "hi": "वेबकैम 1080p", "zh": "1080p 摄像头"},
        {"id": "P010", "price": 35.00, "en": "Mouse Pad XL", "es": "Alfombrilla de ratón XL", "fr": "Tapis de souris XL", "de": "Mauspad XL", "hi": "माउस पैड XL", "zh": "XL 鼠标垫"}
    ]
    
    data = []
    
    # Generate 500 records by sampling from catalog with different languages
    for _ in range(500):
        item = random.choice(products_catalog)
        lang = random.choice(['en', 'es', 'fr', 'de', 'hi', 'zh'])
        
        lang_map = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 
            'de': 'German', 'hi': 'Hindi', 'zh': 'Chinese'
        }
        
        # Introduce a slight price variation for some duplicates (e.g. currency differences/regional pricing)
        price_variation = item['price'] * random.uniform(0.9, 1.1)
        
        record = {
            'ProductID': item['id'],
            'ProductName': item[lang],
            'Language': lang_map[lang],
            'Price': round(price_variation, 2),
            'Stock': random.randint(0, 500)
        }
        data.append(record)
        
    df = pd.DataFrame(data)
    
    # Introduce some noise/missing values
    mask = np.random.rand(len(df)) < 0.05
    df.loc[mask, 'Price'] = np.nan
    
    df = df.sample(frac=1).reset_index(drop=True)
    df.to_csv('multilingual_product_catalog.csv', index=False, encoding='utf-8-sig')
    print("Created multilingual_product_catalog.csv")

if __name__ == "__main__":
    print("Generating multilingual datasets...")
    generate_multilingual_customers()
    generate_multilingual_products()
    print("Done!")
