import pandas as pd
import numpy as np
from faker import Faker
import random
import os
import time
from deep_translator import GoogleTranslator

fake = Faker('en_IN')
Faker.seed(101)
np.random.seed(101)
random.seed(101)

def make_10_digit_phone():
    return f"{random.randint(6,9)}{random.randint(100,999)}{random.randint(1000,9999)}"

def generate_multilingual_dataset(num_records=200, dup_count=50):
    print(f"Generating base dataset of {num_records} records...")
    data = []
    
    for _ in range(num_records):
        record = {
            'CustomerID': f"CUST-{fake.unique.random_number(digits=6)}",
            'FullName': fake.name(),
            'City': fake.city(),
            'State': fake.state(),
            'Phone': make_10_digit_phone(),
            'Email': fake.email(),
            'Language': 'en'
        }
        data.append(record)
        
    df = pd.DataFrame(data)
    
    # Select records to duplicate in other languages
    print(f"Translating {dup_count} records to create multilingual duplicates...")
    records_to_duplicate = df.sample(n=dup_count)
    
    target_langs = ['hi', 'bn', 'ta', 'te', 'mr'] # Hindi, Bengali, Tamil, Telugu, Marathi
    
    multilingual_duplicates = []
    
    for _, row in records_to_duplicate.iterrows():
        lang = random.choice(target_langs)
        try:
            translator = GoogleTranslator(source='en', target=lang)
            translated_name = translator.translate(row['FullName'])
            translated_city = translator.translate(row['City'])
            translated_state = translator.translate(row['State'])
            
            # The Phone, Email, and ID remain the same to simulate the exact same entity 
            # appearing in a different language format
            dup_record = {
                'CustomerID': row['CustomerID'],
                'FullName': translated_name,
                'City': translated_city,
                'State': translated_state,
                'Phone': row['Phone'],
                'Email': row['Email'],
                'Language': lang
            }
            multilingual_duplicates.append(dup_record)
            # Sleep slightly to avoid hitting translation API limits
            time.sleep(0.1)
        except Exception as e:
            print(f"Translation failed for {row['FullName']}: {e}")
            
    df_dups = pd.DataFrame(multilingual_duplicates)
    
    df_combined = pd.concat([df, df_dups], ignore_index=True)
    
    # Shuffle the dataset
    df_combined = df_combined.sample(frac=1).reset_index(drop=True)
    
    # Introduce some standard issues (missing values)
    mask = np.random.rand(len(df_combined)) < 0.05
    df_combined.loc[mask, 'City'] = np.nan
    
    output_path = r'C:\Users\ak656\Desktop\Ai based Automated Data cleaning and Deduplication\Sample datasets\multilingual_indian_customers_with_issues.csv'
    
    df_combined.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Dataset successfully created at: {output_path}")

if __name__ == "__main__":
    generate_multilingual_dataset()
