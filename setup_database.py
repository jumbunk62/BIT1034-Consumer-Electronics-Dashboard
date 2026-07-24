import pandas as pd
import sqlite3
import os
import logging

# Set up logging so you can see what's happening in the terminal
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Define file paths
CSV_FILE = 'consumer_electronics_sales_data.csv'
DB_FILE = 'electronics_sales.db'

def setup_database():
    """Creates the SQLite database and defines the schema."""
    # Delete existing database to start fresh
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        logging.info(f"Deleted existing {DB_FILE} to start fresh.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Products (
            product_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            brand TEXT NOT NULL,
            UNIQUE(category, brand)
        )
    ''')

    # Create Sales Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sales_Transactions (
            transaction_id INTEGER PRIMARY KEY,
            product_type_id INTEGER,
            price REAL,
            customer_age INTEGER,
            customer_gender INTEGER,
            purchase_frequency INTEGER,
            satisfaction_score INTEGER,
            purchase_intent INTEGER,
            FOREIGN KEY (product_type_id) REFERENCES Products (product_type_id)
        )
    ''')
    
    conn.commit()
    logging.info("Database schema created successfully.")
    return conn

def ingest_data(conn):
    """Reads the CSV, maps the data, and inserts it into the database."""
    logging.info(f"Reading data from {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)

    cursor = conn.cursor()

    # 1. Extract unique products and insert into Products table
    unique_products = df[['ProductCategory', 'ProductBrand']].drop_duplicates()
    logging.info(f"Inserting {len(unique_products)} unique product types...")
    
    # Create a mapping dictionary: (Category, Brand) -> product_type_id
    product_map = {}
    for _, row in unique_products.iterrows():
        cursor.execute('''
            INSERT OR IGNORE INTO Products (category, brand) 
            VALUES (?, ?)
        ''', (row['ProductCategory'], row['ProductBrand']))
        
        # Fetch the ID that was just created
        cursor.execute('SELECT product_type_id FROM Products WHERE category=? AND brand=?', 
                       (row['ProductCategory'], row['ProductBrand']))
        product_map[(row['ProductCategory'], row['ProductBrand'])] = cursor.fetchone()[0]

    # 2. Insert transactions into Sales_Transactions table
    logging.info(f"Inserting {len(df)} sales transactions...")
    transaction_data = []
    
    for _, row in df.iterrows():
        # Look up the foreign key
        p_type_id = product_map[(row['ProductCategory'], row['ProductBrand'])]
        
        transaction_data.append((
            row['ProductID'], # We use the original ProductID as our TransactionID
            p_type_id,
            row['ProductPrice'],
            row['CustomerAge'],
            row['CustomerGender'],
            row['PurchaseFrequency'],
            row['CustomerSatisfaction'],
            row['PurchaseIntent']
        ))

    # Batch insert for performance
    cursor.executemany('''
        INSERT INTO Sales_Transactions 
        (transaction_id, product_type_id, price, customer_age, customer_gender, 
         purchase_frequency, satisfaction_score, purchase_intent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', transaction_data)

    conn.commit()
    logging.info("Data ingestion complete!")

if __name__ == "__main__":
    try:
        db_connection = setup_database()
        ingest_data(db_connection)
        db_connection.close()
        logging.info(f"Success! Database saved as '{DB_FILE}'.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")