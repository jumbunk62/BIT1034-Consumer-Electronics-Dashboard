# app.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Electronics Sales Dashboard", 
    layout="wide", 
    page_icon=""
)

# ==========================================
# 2. DATABASE CONNECTION & DATA LOADING
# ==========================================
DB_FILE = 'electronics_sales.db'

# We use @st.cache_data so Streamlit doesn't query the DB every time the user clicks a button
@st.cache_data
def load_data_from_db():
    """Connects to SQLite, joins the normalized tables, and returns a Pandas DataFrame."""
    conn = sqlite3.connect(DB_FILE)
    
    # SQL Query joining Products and Sales_Transactions
    query = """
        SELECT 
            st.transaction_id,
            p.category,
            p.brand,
            st.price,
            st.customer_age,
            st.customer_gender,
            st.purchase_frequency,
            st.satisfaction_score,
            st.purchase_intent
        FROM Sales_Transactions st
        JOIN Products p ON st.product_type_id = p.product_type_id
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Load the data
df = load_data_from_db()

# ==========================================
# 3. SIDEBAR FILTERS
# ==========================================
st.sidebar.title("Filter Data")

# Category Filter
categories = df['category'].unique()
selected_categories = st.sidebar.multiselect(
    "Select Product Category:", 
    options=categories, 
    default=categories
)

# Brand Filter
brands = df['brand'].unique()
selected_brands = st.sidebar.multiselect(
    "Select Brand:", 
    options=brands, 
    default=brands
)

# Age Range Slider
min_age = int(df['customer_age'].min())
max_age = int(df['customer_age'].max())
age_range = st.sidebar.slider(
    "Customer Age Range:", 
    min_value=min_age, 
    max_value=max_age, 
    value=(min_age, max_age)
)

# Purchase Intent Filter
intent_options = {0: "No (0)", 1: "Yes (1)"}
selected_intent = st.sidebar.multiselect(
    "Purchase Intent:",
    options=[0, 1],
    default=[0, 1],
    format_func=lambda x: intent_options[x]
)

# Apply Filters to DataFrame
filtered_df = df[
    (df['category'].isin(selected_categories)) &
    (df['brand'].isin(selected_brands)) &
    (df['customer_age'].between(age_range[0], age_range[1])) &
    (df['purchase_intent'].isin(selected_intent))
]

# ==========================================
# 4. MAIN DASHBOARD LAYOUT
# ==========================================
st.title("Consumer Electronics Sales Dashboard")
st.markdown("An interactive analytics dashboard analyzing sales performance, customer demographics, and satisfaction metrics.")
st.divider()

# --- KEY METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions", f"{len(filtered_df):,}")
col2.metric("Total Revenue", f"${filtered_df['price'].sum():,.2f}")
col3.metric("Avg Satisfaction", f"{filtered_df['satisfaction_score'].mean():.2f} / 5")
intent_rate = filtered_df['purchase_intent'].mean() * 100
col4.metric("Purchase Intent Rate", f"{intent_rate:.1f}%")

st.divider()

# --- VISUALIZATIONS ---
st.subheader("Sales & Performance Analytics")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("**Revenue by Product Category**")
    rev_by_cat = filtered_df.groupby('category')['price'].sum().reset_index()
    fig1 = px.bar(rev_by_cat, x='category', y='price', color='category', 
                  title="Total Revenue by Category", 
                  labels={'price': 'Revenue ($)', 'category': 'Category'})
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.markdown("**Price vs. Customer Satisfaction**")
    fig2 = px.scatter(filtered_df, x='price', y='satisfaction_score', color='category',
                      title="Price vs Satisfaction Score", 
                      labels={'price': 'Price ($)', 'satisfaction_score': 'Satisfaction (1-5)'})
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Customer Demographics & Behavior")

col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("**Top 5 Brands by Sales Volume**")
    brand_counts = filtered_df['brand'].value_counts().head(5).reset_index()
    brand_counts.columns = ['brand', 'count']
    fig3 = px.bar(brand_counts, x='brand', y='count', color='brand', 
                  title="Top 5 Brands by Transaction Count")
    fig3.update_layout(showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

with col_chart4:
    st.markdown("**Customer Age Distribution vs Purchase Intent**")
    fig4 = px.histogram(filtered_df, x='customer_age', nbins=20, color='purchase_intent', 
                        barmode='overlay', title="Age Distribution by Purchase Intent",
                        labels={'customer_age': 'Customer Age', 'count': 'Number of Customers'})
    st.plotly_chart(fig4, use_container_width=True)

# --- RAW DATA TABLE ---
st.subheader("Raw Transaction Data")
st.dataframe(filtered_df, use_container_width=True, height=400)