import pandas as pd
import sqlite3
import os
import logging

# Configure logging to track the script's progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_database(db_name: str) -> sqlite3.Connection:
    """
    Creates a new SQLite database and initializes the normalized schema.
    """
    # Remove existing database to start fresh and avoid duplicate data
    if os.path.exists(db_name):
        os.remove(db_name)
        logging.info(f"Deleted existing database '{db_name}' to start fresh.")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 1. Create Products Table (Eliminates redundancy of categories/brands)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Products (
            product_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            brand TEXT NOT NULL,
            UNIQUE(category, brand)
        )
    ''')

    # 2. Create Sales_Transactions Table (Stores the actual sales events)
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

def ingest_data(csv_path: str, conn: sqlite3.Connection):
    """
    Reads the CSV file, maps the relational data and inserts it into the database.
    """
    logging.info(f"Reading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Data Cleaning: Drop any rows with missing critical values
    if df.isnull().sum().sum() > 0:
        logging.warning("Dataset contains missing values. Dropping rows with NaNs.")
        df.dropna(inplace=True)

    cursor = conn.cursor()

    # --- STEP 1: Populate the Products Table ---
    unique_products = df[['ProductCategory', 'ProductBrand']].drop_duplicates()
    logging.info(f"Inserting {len(unique_products)} unique product types into 'Products' table...")
    
    # Create a dictionary to map (Category, Brand) to the new database ID
    product_map = {}
    for _, row in unique_products.iterrows():
        category = row['ProductCategory']
        brand = row['ProductBrand']
        
        cursor.execute('''
            INSERT OR IGNORE INTO Products (category, brand) 
            VALUES (?, ?)
        ''', (category, brand))
        
        # Fetch the auto-generated product_type_id
        cursor.execute('SELECT product_type_id FROM Products WHERE category=? AND brand=?', 
                       (category, brand))
        product_map[(category, brand)] = cursor.fetchone()[0]

    # --- STEP 2: Populate the Sales_Transactions Table ---
    logging.info(f"Processing {len(df)} sales transactions...")
    transaction_data = []
    
    for _, row in df.iterrows():
        # Map the category and brand to the new relational Foreign Key
        p_type_id = product_map[(row['ProductCategory'], row['ProductBrand'])]
        
        transaction_data.append((
            int(row['ProductID']), # The original 'ProductID' is actually our Transaction ID
            p_type_id,
            float(row['ProductPrice']),
            int(row['CustomerAge']),
            int(row['CustomerGender']),
            int(row['PurchaseFrequency']),
            int(row['CustomerSatisfaction']),
            int(row['PurchaseIntent'])
        ))

    # Batch insert for better performance
    cursor.executemany('''
        INSERT INTO Sales_Transactions 
        (transaction_id, product_type_id, price, customer_age, customer_gender, 
         purchase_frequency, satisfaction_score, purchase_intent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', transaction_data)

    conn.commit()
    logging.info("Data ingestion complete!")

if __name__ == "__main__":
    CSV_FILE = 'consumer_electronics_sales_data.csv'
    DB_FILE = 'electronics_sales.db'
    
    try:
        db_connection = setup_database(DB_FILE)
        ingest_data(CSV_FILE, db_connection)
        db_connection.close()
        logging.info(f"Success! Database saved as '{DB_FILE}'.")
    except Exception as e:
        logging.error(f"An error occurred during ingestion: {e}")