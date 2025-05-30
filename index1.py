import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import uuid 
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
import io
import re
import base64

# Set page configuration
st.set_page_config(
    page_title="Ledger Management System",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File paths for local storage
DATA_DIR = "data"
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CUSTOMER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "customer_transactions")
SUPPLIER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "supplier_transactions")

# Create data directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CUSTOMER_TRANSACTIONS_DIR, exist_ok=True)
os.makedirs(SUPPLIER_TRANSACTIONS_DIR, exist_ok=True)

# Initialize session state variables
if 'settings' not in st.session_state:
    st.session_state.settings = {
        "theme": "dark",
        "auto_backup": True,
        "auto_calculate_balance": True,
        "date_format": "%Y-%m-%d",
        "currency_symbol": "₹",
        "notification_enabled": True,
        "auto_save_interval": 5,
        "auto_date_format": True
    }

if 'current_customer' not in st.session_state:
    st.session_state.current_customer = None
if 'current_supplier' not in st.session_state:
    st.session_state.current_supplier = None
if 'edit_customer' not in st.session_state:
    st.session_state.edit_customer = None
if 'edit_supplier' not in st.session_state:
    st.session_state.edit_supplier = None
if 'edit_transaction' not in st.session_state:
    st.session_state.edit_transaction = None
if 'confirm_delete_customer' not in st.session_state:
    st.session_state.confirm_delete_customer = None
if 'confirm_delete_supplier' not in st.session_state:
    st.session_state.confirm_delete_supplier = None

# Apply dark theme
def apply_theme():
    st.markdown("""
    <style>
    /* Base elements */
    .stApp, .stTabs, .main {
        background-color: #121212 !important;
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #BB86FC !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
    }
    
    h4, h5, h6 {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #BB86FC !important;
        color: #FFFFFF !important;
        border-radius: 5px !important;
        font-weight: bold !important;
        border: 1px solid #BB86FC !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #9965F4 !important;
        border-color: #9965F4 !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.4) !important;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input, .stDateInput>div>div>input {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: 1px solid #2C2C2C !important;
        border-radius: 4px !important;
        padding: 0.5rem !important;
    }
    
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus, .stNumberInput>div>div>input:focus {
        border-color: #BB86FC !important;
        box-shadow: 0 0 0 2px rgba(187, 134, 252, 0.3) !important;
    }
    
    /* Text areas */
    .stTextArea>div>div>textarea {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: 1px solid #2C2C2C !important;
        border-radius: 4px !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        background-color: #1E1E1E !important;
        border: 1px solid #2C2C2C !important;
        border-radius: 8px !important;
    }
    
    /* Metric cards */
    .metric-card {
        background: #1E1E1E !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        border-radius: 8px !important;
        padding: 1.2rem !important;
        margin-bottom: 1rem !important;
        border: 1px solid #2C2C2C !important;
        transition: transform 0.3s ease !important;
    }
    .metric-card:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
        border-color: #BB86FC !important;
    }
    .metric-value {
        font-size: 28px !important;
        font-weight: bold !important;
        color: #BB86FC !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
    }
    .metric-label {
        font-size: 16px !important;
        color: #B0B0B0 !important;
        font-weight: 500 !important;
    }
    
    /* Forms */
    .stForm {
        background-color: #1E1E1E !important;
        padding: 25px !important;
        border-radius: 10px !important;
        border: 1px solid #2C2C2C !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1E1E1E !important;
        border-right: 1px solid #2C2C2C !important;
    }
    
    /* Labels */
    .stTextInput>div>label, .stSelectbox>div>label, .stNumberInput>div>label, 
    .stTextArea>div>label, .stDateInput>div>label {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_theme()

# Utility functions
def format_currency(amount):
    currency_symbol = st.session_state.settings["currency_symbol"]
    return f"{currency_symbol}{amount:,.2f}"

def format_date(date_str):
    try:
        date_format = st.session_state.settings["date_format"]
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(date_format)
    except:
        return date_str

def validate_date(date_str):
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def calculate_balance(transactions_list):
    balance = 0
    for transaction in transactions_list:
        debit = float(transaction.get('debit', 0))
        credit = float(transaction.get('credit', 0))
        balance += credit - debit
    return balance

# Data management functions
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Ensure all required keys exist
                required_keys = {
                    "theme": "dark",
                    "auto_backup": True,
                    "auto_calculate_balance": True,
                    "date_format": "%Y-%m-%d",
                    "currency_symbol": "₹",
                    "notification_enabled": True,
                    "auto_save_interval": 5,
                    "auto_date_format": True
                }
                for key, default_value in required_keys.items():
                    if key not in settings:
                        settings[key] = default_value
                return settings
    except Exception as e:
        st.error(f"Error loading settings: {e}")
    
    # Default settings
    return {
        "theme": "dark",
        "auto_backup": True,
        "auto_calculate_balance": True,
        "date_format": "%Y-%m-%d",
        "currency_symbol": "₹",
        "notification_enabled": True,
        "auto_save_interval": 5,
        "auto_date_format": True
    }

def save_settings(settings_data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving settings: {e}")
        return False

def load_customers():
    try:
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading customers: {e}")
    return {}

def save_customer(customer_id, customer_data):
    try:
        customers = load_customers()
        customers[customer_id] = customer_data
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving customer: {e}")
        return False

def delete_customer(customer_id):
    try:
        customers = load_customers()
        if customer_id in customers:
            del customers[customer_id]
            with open(CUSTOMERS_FILE, 'w') as f:
                json.dump(customers, f, indent=2)
            
            # Delete transactions
            customer_trans_file = os.path.join(CUSTOMER_TRANSACTIONS_DIR, f"{customer_id}.json")
            if os.path.exists(customer_trans_file):
                os.remove(customer_trans_file)
            
            return True
    except Exception as e:
        st.error(f"Error deleting customer: {e}")
        return False

def load_suppliers():
    try:
        if os.path.exists(SUPPLIERS_FILE):
            with open(SUPPLIERS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading suppliers: {e}")
    return {}

def save_supplier(supplier_id, supplier_data):
    try:
        suppliers = load_suppliers()
        suppliers[supplier_id] = supplier_data
        with open(SUPPLIERS_FILE, 'w') as f:
            json.dump(suppliers, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving supplier: {e}")
        return False

def delete_supplier(supplier_id):
    try:
        suppliers = load_suppliers()
        if supplier_id in suppliers:
            del suppliers[supplier_id]
            with open(SUPPLIERS_FILE, 'w') as f:
                json.dump(suppliers, f, indent=2)
            
            # Delete transactions
            supplier_trans_file = os.path.join(SUPPLIER_TRANSACTIONS_DIR, f"{supplier_id}.json")
            if os.path.exists(supplier_trans_file):
                os.remove(supplier_trans_file)
            
            return True
    except Exception as e:
        st.error(f"Error deleting supplier: {e}")
        return False

def load_transactions(entity_type, entity_id):
    try:
        trans_file = os.path.join(
            CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
            f"{entity_id}.json"
        )
        
        if os.path.exists(trans_file):
            with open(trans_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
    return {}

def save_transaction(entity_type, entity_id, transaction_id, transaction_data):
    try:
        trans_file = os.path.join(
            CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
            f"{entity_id}.json"
        )
        
        transactions = {}
        if os.path.exists(trans_file):
            with open(trans_file, 'r') as f:
                transactions = json.load(f)
        
        transactions[transaction_id] = transaction_data
        
        with open(trans_file, 'w') as f:
            json.dump(transactions, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving transaction: {e}")
        return False

def delete_transaction(entity_type, entity_id, transaction_id):
    try:
        trans_file = os.path.join(
            CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
            f"{entity_id}.json"
        )
        
        if os.path.exists(trans_file):
            with open(trans_file, 'r') as f:
                transactions = json.load(f)
            
            if transaction_id in transactions:
                del transactions[transaction_id]
                
                with open(trans_file, 'w') as f:
                    json.dump(transactions, f, indent=2)
                
                return True
    except Exception as e:
        st.error(f"Error deleting transaction: {e}")
        return False


def save_excel_file(dataframe, default_filename="ledger_export.xlsx"):
    """Save dataframe as Excel file"""
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False)
    
    excel_data = buffer.getvalue()
    
    st.download_button(
        label="📥 Download Excel File",
        data=excel_data,
        file_name=default_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    return True

# Load settings at startup
st.session_state.settings = load_settings()

# Main app title
st.title("📒 Ledger Management System")

# Sidebar status
st.sidebar.markdown("---")
st.sidebar.subheader("📊 System Status")
st.sidebar.markdown("💾 **Storage:** Local Files")
st.sidebar.markdown("📱 **Mode:** Offline")

try:
    customers_count = len(load_customers())
    suppliers_count = len(load_suppliers())
    st.sidebar.markdown(f"👥 **Customers:** {customers_count}")
    st.sidebar.markdown(f"🏢 **Suppliers:** {suppliers_count}")
except:
    st.sidebar.markdown("📊 **Data:** Loading...")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Customers", "🏢 Suppliers", "⚙️ Settings"])

# Dashboard Tab
with tab1:
    st.header("📊 Dashboard")
    
    # Load all data for dashboard
    all_customers = load_customers()
    all_suppliers = load_suppliers()
    
    # Calculate total receivables and payables
    total_receivable = 0
    total_payable = 0
    
    for customer_id, customer in all_customers.items():
        customer_transactions = load_transactions("customer", customer_id)
        if customer_transactions:
            customer_balance = calculate_balance(list(customer_transactions.values()))
            if customer_balance > 0:
                total_receivable += customer_balance
            else:
                total_payable -= customer_balance
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = load_transactions("supplier", supplier_id)
        if supplier_transactions:
            supplier_balance = calculate_balance(list(supplier_transactions.values()))
            if supplier_balance < 0:
                total_payable -= supplier_balance
            else:
                total_receivable += supplier_balance
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #1E1E1E; border: 1px solid #4CAF50;">
            <div class="metric-value" style="color: #4CAF50;">{format_currency(total_receivable)}</div>
            <div class="metric-label">You Get (Total Receivable)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #1E1E1E; border: 1px solid #F44336;">
            <div class="metric-value" style="color: #F44336;">{format_currency(total_payable)}</div>
            <div class="metric-label">You Give (Total Payable)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        net_balance = total_receivable - total_payable
        color = "#4CAF50" if net_balance >= 0 else "#F44336"
        
        st.markdown(f"""
        <div class="metric-card" style="background-color: #1E1E1E; border: 1px solid {color};">
            <div class="metric-value" style="color: {color};">{format_currency(net_balance)}</div>
            <div class="metric-label">Net Balance</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display customer and supplier counts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #1E1E1E; border: 1px solid #BB86FC;">
            <div class="metric-value" style="color: #BB86FC;">{len(all_customers)}</div>
            <div class="metric-label">Total Customers</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #1E1E1E; border: 1px solid #FF9800;">
            <div class="metric-value" style="color: #FF9800;">{len(all_suppliers)}</div>
            <div class="metric-label">Total Suppliers</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent transactions
    st.subheader("📋 Recent Transactions")
    
    # Combine all transactions
    all_transactions = []
    
    for customer_id, customer in all_customers.items():
        customer_transactions = load_transactions("customer", customer_id)
        if customer_transactions:
            for trans_id, transaction in customer_transactions.items():
                transaction['entity_name'] = customer.get('name', 'Unknown')
                transaction['entity_type'] = 'Customer'
                transaction['id'] = trans_id
                transaction['entity_id'] = customer_id
                all_transactions.append(transaction)
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = load_transactions("supplier", supplier_id)
        if supplier_transactions:
            for trans_id, transaction in supplier_transactions.items():
                transaction['entity_name'] = supplier.get('name', 'Unknown')
                transaction['entity_type'] = 'Supplier'
                transaction['id'] = trans_id
                transaction['entity_id'] = supplier_id
                all_transactions.append(transaction)
    
    # Sort by date (most recent first)
    all_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Display recent transactions (top 10)
    if all_transactions:
        recent_transactions = all_transactions[:10]
        
        # Create DataFrame for display
        df_transactions = []
        
        for transaction in recent_transactions:
            debit = float(transaction.get('debit', 0))
            credit = float(transaction.get('credit', 0))
            
            df_transactions.append({
                "Date": format_date(transaction.get('date', '')),
                "Entity": f"{transaction.get('entity_name', '')} ({transaction.get('entity_type', '')})",
                "Particulars": transaction.get('particular', ''),
                "Debit": format_currency(debit) if debit > 0 else "",
                "Credit": format_currency(credit) if credit > 0 else ""
            })
        
        df = pd.DataFrame(df_transactions)
        st.dataframe(df, use_container_width=True)
        
    else:
        st.info("No transactions found. Add your first transaction in the Customers or Suppliers tab.")
    
    # Financial charts
    if all_transactions:
        st.subheader("📈 Financial Overview")
        
        # Prepare data for charts
        monthly_data = {}
        
        for transaction in all_transactions:
            try:
                date_parts = transaction.get('date', '').split('-')
                if len(date_parts) >= 2:
                    year_month = f"{date_parts[0]}-{date_parts[1]}"
                    
                    if year_month not in monthly_data:
                        monthly_data[year_month] = {'debit': 0, 'credit': 0}
                    
                    debit = float(transaction.get('debit', 0))
                    credit = float(transaction.get('credit', 0))
                    
                    monthly_data[year_month]['debit'] += debit
                    monthly_data[year_month]['credit'] += credit
            except:
                pass
        
        # Create DataFrame for chart
        chart_data = []
        for month, values in monthly_data.items():
            chart_data.append({
                'Month': month,
                'Debit': values['debit'],
                'Credit': values['credit'],
                'Net': values['credit'] - values['debit']
            })
        
        chart_df = pd.DataFrame(chart_data)
        
        if not chart_df.empty:
            # Sort by month
            chart_df = chart_df.sort_values('Month')
            
            # Create charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Line chart for debit and credit
                fig = px.line(
                    chart_df, 
                    x='Month', 
                    y=['Debit', 'Credit'],
                    title='Monthly Debit and Credit',
                    labels={'value': 'Amount', 'variable': 'Type'},
                    color_discrete_map={'Debit': '#FF6B6B', 'Credit': '#4CAF50'}
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Bar chart for net balance
                fig = px.bar(
                    chart_df,
                    x='Month',
                    y='Net',
                    title='Monthly Net Balance',
                    labels={'Net': 'Net Balance'},
                    color='Net',
                    color_continuous_scale=['#FF6B6B', '#FFFFFF', '#4CAF50'],
                    color_continuous_midpoint=0
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)

# Customers Tab
with tab2:
    st.header("👥 Customers")
    
    # Add new customer form
    with st.expander("➕ Add New Customer", expanded=False):
        with st.form("add_customer_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Customer Name*")
                new_phone = st.text_input("Phone Number*")
            
            with col2:
                new_email = st.text_input("Email (Optional)")
                new_address = st.text_area("Address (Optional)")
            
            submitted = st.form_submit_button("Add Customer")
            if submitted:
                if not new_name or not new_phone:
                    st.error("Name and Phone Number are required!")
                else:
                    # Check if customer with same phone already exists
                    all_customers = load_customers()
                    exists = False
                    for customer in all_customers.values():
                        if customer.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"Customer with phone number {new_phone} already exists!")
                    else:
                        customer_id = str(uuid.uuid4())
                        customer_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if save_customer(customer_id, customer_data):
                            st.success(f"Customer {new_name} added successfully!")
                            st.rerun()
    
    # Search and filter customers
    all_customers = load_customers()
    
    if not all_customers:
        st.info("No customers found. Add your first customer using the form above.")
    else:
        # Search box
        search_query = st.text_input("🔍 Search customers by name or phone", "")
        
        # Filter customers based on search query
        filtered_customers = {}
        for customer_id, customer in all_customers.items():
            if (search_query.lower() in customer.get('name', '').lower() or 
                search_query in customer.get('phone', '')):
                filtered_customers[customer_id] = customer
        
        # Display customers in a table
        if filtered_customers:
            # Prepare data for display
            customer_data = []
            
            for customer_id, customer in filtered_customers.items():
                # Load transactions for this customer
                transactions = load_transactions("customer", customer_id)
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Add to display data
                customer_data.append({
                    "ID": customer_id,
                    "Name": customer.get('name', ''),
                    "Phone": customer.get('phone', ''),
                    "Balance": format_currency(balance),
                    "Status": "Due" if balance > 0 else "Advance" if balance < 0 else "Settled"
                })
            
            # Create DataFrame
            df = pd.DataFrame(customer_data)
            
            # Display table
            st.dataframe(df.set_index("ID"), use_container_width=True)
            
            # Customer selection for detailed view
            selected_customer_id = st.selectbox(
                "Select customer to view details",
                options=list(filtered_customers.keys()),
                format_func=lambda x: filtered_customers[x].get('name', 'Unknown'),
                key="customer_select"
            )
            
            if selected_customer_id:
                st.session_state.current_customer = selected_customer_id
        else:
            st.info("No customers match your search criteria.")
    
    # Display customer profile and ledger
    if st.session_state.current_customer:
        customer_id = st.session_state.current_customer
        customer = all_customers.get(customer_id, {})
        
        if customer:
            # Customer profile section
            st.subheader(f"👤 Customer Profile: {customer.get('name', 'Unknown')}")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**📞 Phone:** {customer.get('phone', 'N/A')}")
                st.write(f"**📧 Email:** {customer.get('email', 'N/A')}")
                st.write(f"**📍 Address:** {customer.get('address', 'N/A')}")
                st.write(f"**📅 Customer since:** {format_date(customer.get('created_on', 'N/A'))}")
            
            with col2:
                # Load transactions
                transactions = load_transactions("customer", customer_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                # Display balance
                balance_color = "#F44336" if balance > 0 else "#4CAF50" if balance < 0 else "#FFC107"
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <h3 style="margin: 0;">Balance: {format_currency(balance)}</h3>
                    <p style="margin: 0;">Status: {"Due" if balance > 0 else "Advance" if balance < 0 else "Settled"}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("✏️ Edit Customer", key=f"edit_customer_{customer_id}"):
                    st.session_state.edit_customer = customer_id
                
                if st.button("🗑️ Delete Customer", key=f"delete_customer_{customer_id}"):
                    st.session_state.confirm_delete_customer = customer_id
            
            # Edit customer form
            if st.session_state.edit_customer == customer_id:
                with st.form(f"edit_customer_form_{customer_id}"):
                    st.subheader("✏️ Edit Customer")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Customer Name*", value=customer.get('name', ''))
                        edit_phone = st.text_input("Phone Number*", value=customer.get('phone', ''))
                    
                    with col2:
                        edit_email = st.text_input("Email", value=customer.get('email', ''))
                        edit_address = st.text_area("Address", value=customer.get('address', ''))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_submitted = st.form_submit_button("Update Customer")
                    
                    with col2:
                        cancel = st.form_submit_button("Cancel")
                    
                    if update_submitted:
                        if not edit_name or not edit_phone:
                            st.error("Name and Phone Number are required!")
                        else:
                            # Check if phone number is already used by another customer
                            phone_exists = False
                            for cid, cust in all_customers.items():
                                if cid != customer_id and cust.get('phone') == edit_phone:
                                    phone_exists = True
                                    break
                            
                            if phone_exists:
                                st.error(f"Phone number {edit_phone} is already used by another customer!")
                            else:
                                # Update customer data
                                updated_customer = {
                                    'name': edit_name,
                                    'phone': edit_phone,
                                    'email': edit_email,
                                    'address': edit_address,
                                    'created_on': customer.get('created_on', datetime.datetime.now().strftime('%Y-%m-%d'))
                                }
                                
                                if save_customer(customer_id, updated_customer):
                                    st.success("Customer updated successfully!")
                                    st.session_state.edit_customer = None
                                    st.rerun()
                    
                    if cancel:
                        st.session_state.edit_customer = None
                        st.rerun()
            
            # Confirm delete dialog
            if st.session_state.confirm_delete_customer == customer_id:
                st.warning(f"⚠️ Are you sure you want to delete customer '{customer.get('name', 'Unknown')}'? This will also delete all transactions.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Yes, Delete", key=f"confirm_delete_customer_{customer_id}"):
                        if delete_customer(customer_id):
                            st.success("Customer deleted successfully!")
                            st.session_state.confirm_delete_customer = None
                            st.session_state.current_customer = None
                            st.rerun()
                
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_customer_{customer_id}"):
                        st.session_state.confirm_delete_customer = None
                        st.rerun()
            
            # Customer ledger section
            st.subheader("📖 Ledger Book")
            
            # Add new transaction
            with st.expander("➕ Add New Transaction", expanded=False):
                with st.form(f"add_customer_transaction_form_{customer_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_input = st.date_input(
                            "Date*",
                            value=datetime.datetime.now().date(),
                            key=f"customer_date_input_{customer_id}"
                        )
                        
                        particular = st.text_area(
                            "Particulars*", 
                            help="Description of the transaction",
                            key=f"customer_particular_{customer_id}"
                        )
                    
                    with col2:
                        debit = st.number_input(
                            "Debit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount customer pays (reduces their debt)",
                            key=f"customer_debit_{customer_id}"
                        )
                        
                        credit = st.number_input(
                            "Credit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount customer owes (increases their debt)",
                            key=f"customer_credit_{customer_id}"
                        )
                    
                    transaction_submitted = st.form_submit_button("Add Transaction")
                    
                    if transaction_submitted:
                        if not particular:
                            st.error("Particulars are required!")
                        elif debit == 0 and credit == 0:
                            st.error("Either Debit or Credit amount must be greater than zero!")
                        else:
                            transaction_id = str(uuid.uuid4())
                            transaction_data = {
                                'date': str(date_input),
                                'particular': particular,
                                'debit': str(debit),
                                'credit': str(credit)
                            }
                            
                            if save_transaction("customer", customer_id, transaction_id, transaction_data):
                                st.success("Transaction added successfully!")
                                st.rerun()
            
            # Display transactions
            transactions = load_transactions("customer", customer_id)
            
            if not transactions:
                st.info("No transactions recorded yet.")
            else:
                # Convert to list and sort by date
                transactions_list = list(transactions.values())
                for t in transactions_list:
                    t['id'] = next((k for k, v in transactions.items() if v == t), None)
                
                transactions_list.sort(key=lambda x: x.get('date', ''))
                
                # Create DataFrame for display
                df_transactions = []
                running_balance = 0
                total_debit = 0
                total_credit = 0
                
                for transaction in transactions_list:
                    debit = float(transaction.get('debit', 0))
                    credit = float(transaction.get('credit', 0))
                    running_balance += credit - debit
                    total_debit += debit
                    total_credit += credit
                    
                    df_transactions.append({
                        "ID": transaction.get('id', ''),
                        "Date": format_date(transaction.get('date', '')),
                        "Particulars": transaction.get('particular', ''),
                        "Debit": format_currency(debit) if debit > 0 else "",
                        "Credit": format_currency(credit) if credit > 0 else "",
                        "Balance": format_currency(running_balance)
                    })
                
                # Add totals row
                df_transactions.append({
                    "ID": "",
                    "Date": "",
                    "Particulars": "TOTAL",
                    "Debit": format_currency(total_debit),
                    "Credit": format_currency(total_credit),
                    "Balance": format_currency(running_balance)
                })
                
                df = pd.DataFrame(df_transactions)
                st.dataframe(df.set_index("ID"), use_container_width=True)
                
                # Export to Excel
                if st.button("📥 Export Ledger to Excel", key=f"export_customer_{customer_id}"):
                    # Create a more detailed DataFrame for export
                    export_df = pd.DataFrame([
                        {
                            "Date": t.get('date', ''),
                            "Particulars": t.get('particular', ''),
                            "Debit": float(t.get('debit', 0)),
                            "Credit": float(t.get('credit', 0))
                        } for t in transactions_list
                    ])
                    
                    # Calculate running balance
                    balance = 0
                    balances = []
                    for _, row in export_df.iterrows():
                        balance += row['Credit'] - row['Debit']
                        balances.append(balance)
                    
                    export_df['Balance'] = balances
                    
                    # Add totals row
                    export_df.loc[len(export_df)] = [
                        "", "TOTAL", 
                        export_df['Debit'].sum(), 
                        export_df['Credit'].sum(), 
                        balance
                    ]
                    
                    # Save to Excel using Streamlit download button
                    filename = f"customer_ledger_{customer.get('name', 'unknown').replace(' ', '_')}.xlsx"
                    save_excel_file(export_df, filename)
                
                # Transaction actions
                st.subheader("⚙️ Transaction Actions")
                
                if len(transactions_list) > 0:
                    selected_transaction_id = st.selectbox(
                        "Select transaction",
                        options=[t.get('id', '') for t in transactions_list if t.get('id', '')],
                        format_func=lambda x: next((f"{t.get('date', '')} - {t.get('particular', '')}" for t in transactions_list if t.get('id', '') == x), ""),
                        key="customer_transaction_select"
                    )
                    
                    if selected_transaction_id:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✏️ Edit Transaction", key=f"edit_customer_trans_{selected_transaction_id}"):
                                st.session_state.edit_transaction = {
                                    'id': selected_transaction_id,
                                    'entity_type': 'customer',
                                    'entity_id': customer_id
                                }
                        
                        with col2:
                            if st.button("🗑️ Delete Transaction", key=f"delete_customer_trans_{selected_transaction_id}"):
                                if delete_transaction("customer", customer_id, selected_transaction_id):
                                    st.success("Transaction deleted successfully!")
                                    st.rerun()
            
            # Edit transaction form
            if (st.session_state.edit_transaction and 
                st.session_state.edit_transaction['entity_type'] == 'customer' and 
                st.session_state.edit_transaction['entity_id'] == customer_id):
                
                transaction_id = st.session_state.edit_transaction['id']
                transaction = transactions.get(transaction_id, {})
                
                if transaction:
                    with st.form(f"edit_customer_transaction_form_{transaction_id}"):
                        st.subheader("✏️ Edit Transaction")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            try:
                                current_date = datetime.datetime.strptime(transaction.get('date', ''), '%Y-%m-%d').date()
                            except:
                                current_date = datetime.datetime.now().date()
                            
                            edit_date = st.date_input(
                                "Date*",
                                value=current_date,
                                key=f"edit_customer_date_{transaction_id}"
                            )
                            
                            edit_particular = st.text_area(
                                "Particulars*", 
                                value=transaction.get('particular', ''),
                                help="Description of the transaction",
                                key=f"edit_customer_particular_{transaction_id}"
                            )
                        
                        with col2:
                            edit_debit = st.number_input(
                                "Debit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('debit', 0)),
                                format="%.2f",
                                help="Amount customer pays (reduces their debt)",
                                key=f"edit_customer_debit_{transaction_id}"
                            )
                            
                            edit_credit = st.number_input(
                                "Credit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('credit', 0)),
                                format="%.2f",
                                help="Amount customer owes (increases their debt)",
                                key=f"edit_customer_credit_{transaction_id}"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            update_trans_submitted = st.form_submit_button("Update Transaction")
                        
                        with col2:
                            cancel_trans = st.form_submit_button("Cancel")
                        
                        if update_trans_submitted:
                            if not edit_particular:
                                st.error("Particulars are required!")
                            elif edit_debit == 0 and edit_credit == 0:
                                st.error("Either Debit or Credit amount must be greater than zero!")
                            else:
                                updated_transaction = {
                                    'date': str(edit_date),
                                    'particular': edit_particular,
                                    'debit': str(edit_debit),
                                    'credit': str(edit_credit)
                                }
                                
                                if save_transaction("customer", customer_id, transaction_id, updated_transaction):
                                    st.success("Transaction updated successfully!")
                                    st.session_state.edit_transaction = None
                                    st.rerun()
                        
                        if cancel_trans:
                            st.session_state.edit_transaction = None
                            st.rerun()

# Suppliers Tab
with tab3:
    st.header("🏢 Suppliers")
    
    # Add new supplier form
    with st.expander("➕ Add New Supplier", expanded=False):
        with st.form("add_supplier_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Supplier Name*", key="supplier_name")
                new_phone = st.text_input("Phone Number*", key="supplier_phone")
            
            with col2:
                new_email = st.text_input("Email (Optional)", key="supplier_email")
                new_address = st.text_area("Address (Optional)", key="supplier_address")
            
            submitted = st.form_submit_button("Add Supplier")
            if submitted:
                if not new_name or not new_phone:
                    st.error("Name and Phone Number are required!")
                else:
                    # Check if supplier with same phone already exists
                    all_suppliers = load_suppliers()
                    exists = False
                    for supplier in all_suppliers.values():
                        if supplier.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"Supplier with phone number {new_phone} already exists!")
                    else:
                        supplier_id = str(uuid.uuid4())
                        supplier_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if save_supplier(supplier_id, supplier_data):
                            st.success(f"Supplier {new_name} added successfully!")
                            st.rerun()
    
    # Search and filter suppliers
    all_suppliers = load_suppliers()
    
    if not all_suppliers:
        st.info("No suppliers found. Add your first supplier using the form above.")
    else:
        # Search box
        search_query = st.text_input("🔍 Search suppliers by name or phone", "", key="supplier_search")
        
        # Filter suppliers based on search query
        filtered_suppliers = {}
        for supplier_id, supplier in all_suppliers.items():
            if (search_query.lower() in supplier.get('name', '').lower() or 
                search_query in supplier.get('phone', '')):
                filtered_suppliers[supplier_id] = supplier
        
        # Display suppliers in a table
        if filtered_suppliers:
            # Prepare data for display
            supplier_data = []
            
            for supplier_id, supplier in filtered_suppliers.items():
                # Load transactions for this supplier
                transactions = load_transactions("supplier", supplier_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Add to display data
                supplier_data.append({
                    "ID": supplier_id,
                    "Name": supplier.get('name', ''),
                    "Phone": supplier.get('phone', ''),
                    "Balance": format_currency(balance),
                    "Status": "Due" if balance < 0 else "Advance" if balance > 0 else "Settled"
                })
            
            # Create DataFrame
            df = pd.DataFrame(supplier_data)
            
            # Display table
            st.dataframe(df.set_index("ID"), use_container_width=True)
            
            # Supplier selection for detailed view
            selected_supplier_id = st.selectbox(
                "Select supplier to view details",
                options=list(filtered_suppliers.keys()),
                format_func=lambda x: filtered_suppliers[x].get('name', 'Unknown'),
                key="supplier_select"
            )
            
            if selected_supplier_id:
                st.session_state.current_supplier = selected_supplier_id
        else:
            st.info("No suppliers match your search criteria.")
    
    # Display supplier profile and ledger
    if st.session_state.current_supplier:
        supplier_id = st.session_state.current_supplier
        supplier = all_suppliers.get(supplier_id, {})
        
        if supplier:
            # Supplier profile section
            st.subheader(f"🏢 Supplier Profile: {supplier.get('name', 'Unknown')}")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**📞 Phone:** {supplier.get('phone', 'N/A')}")
                st.write(f"**📧 Email:** {supplier.get('email', 'N/A')}")
                st.write(f"**📍 Address:** {supplier.get('address', 'N/A')}")
                st.write(f"**📅 Supplier since:** {format_date(supplier.get('created_on', 'N/A'))}")
            
            with col2:
                # Load transactions
                transactions = load_transactions("supplier", supplier_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Display balance
                balance_color = "#F44336" if balance < 0 else "#4CAF50" if balance > 0 else "#FFC107"
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <h3 style="margin: 0;">Balance: {format_currency(balance)}</h3>
                    <p style="margin: 0;">Status: {"Due" if balance < 0 else "Advance" if balance > 0 else "Settled"}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("✏️ Edit Supplier", key=f"edit_supplier_{supplier_id}"):
                    st.session_state.edit_supplier = supplier_id
                
                if st.button("🗑️ Delete Supplier", key=f"delete_supplier_{supplier_id}"):
                    st.session_state.confirm_delete_supplier = supplier_id
            
            # Edit supplier form
            if st.session_state.edit_supplier == supplier_id:
                with st.form(f"edit_supplier_form_{supplier_id}"):
                    st.subheader("✏️ Edit Supplier")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Supplier Name*", value=supplier.get('name', ''))
                        edit_phone = st.text_input("Phone Number*", value=supplier.get('phone', ''))
                    
                    with col2:
                        edit_email = st.text_input("Email", value=supplier.get('email', ''))
                        edit_address = st.text_area("Address", value=supplier.get('address', ''))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_submitted = st.form_submit_button("Update Supplier")
                    
                    with col2:
                        cancel = st.form_submit_button("Cancel")
                    
                    if update_submitted:
                        if not edit_name or not edit_phone:
                            st.error("Name and Phone Number are required!")
                        else:
                            # Check if phone number is already used by another supplier
                            phone_exists = False
                            for sid, supp in all_suppliers.items():
                                if sid != supplier_id and supp.get('phone') == edit_phone:
                                    phone_exists = True
                                    break
                            
                            if phone_exists:
                                st.error(f"Phone number {edit_phone} is already used by another supplier!")
                            else:
                                # Update supplier data
                                updated_supplier = {
                                    'name': edit_name,
                                    'phone': edit_phone,
                                    'email': edit_email,
                                    'address': edit_address,
                                    'created_on': supplier.get('created_on', datetime.datetime.now().strftime('%Y-%m-%d'))
                                }
                                
                                if save_supplier(supplier_id, updated_supplier):
                                    st.success("Supplier updated successfully!")
                                    st.session_state.edit_supplier = None
                                    st.rerun()
                    
                    if cancel:
                        st.session_state.edit_supplier = None
                        st.rerun()
            
            # Confirm delete dialog
            if st.session_state.confirm_delete_supplier == supplier_id:
                st.warning(f"⚠️ Are you sure you want to delete supplier '{supplier.get('name', 'Unknown')}'? This will also delete all transactions.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Yes, Delete", key=f"confirm_delete_supplier_{supplier_id}"):
                        if delete_supplier(supplier_id):
                            st.success("Supplier deleted successfully!")
                            st.session_state.confirm_delete_supplier = None
                            st.session_state.current_supplier = None
                            st.rerun()
                
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_supplier_{supplier_id}"):
                        st.session_state.confirm_delete_supplier = None
                        st.rerun()
            
            # Supplier ledger section
            st.subheader("📖 Ledger Book")
            
            # Add new transaction
            with st.expander("➕ Add New Transaction", expanded=False):
                with st.form(f"add_supplier_transaction_form_{supplier_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_input = st.date_input(
                            "Date*",
                            value=datetime.datetime.now().date(),
                            key=f"supplier_date_input_{supplier_id}"
                        )
                        
                        particular = st.text_area(
                            "Particulars*", 
                            help="Description of the transaction",
                            key=f"supplier_particular_{supplier_id}"
                        )
                    
                    with col2:
                        debit = st.number_input(
                            "Debit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount you pay to supplier",
                            key=f"supplier_debit_{supplier_id}"
                        )
                        
                        credit = st.number_input(
                            "Credit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount you owe to supplier",
                            key=f"supplier_credit_{supplier_id}"
                        )
                    
                    transaction_submitted = st.form_submit_button("Add Transaction")
                    
                    if transaction_submitted:
                        if not particular:
                            st.error("Particulars are required!")
                        elif debit == 0 and credit == 0:
                            st.error("Either Debit or Credit amount must be greater than zero!")
                        else:
                            transaction_id = str(uuid.uuid4())
                            transaction_data = {
                                'date': str(date_input),
                                'particular': particular,
                                'debit': str(debit),
                                'credit': str(credit)
                            }
                            
                            if save_transaction("supplier", supplier_id, transaction_id, transaction_data):
                                st.success("Transaction added successfully!")
                                st.rerun()
            
            # Display transactions
            transactions = load_transactions("supplier", supplier_id)
            
            if not transactions:
                st.info("No transactions recorded yet.")
            else:
                # Convert to list and sort by date
                transactions_list = list(transactions.values())
                for t in transactions_list:
                    t['id'] = next((k for k, v in transactions.items() if v == t), None)
                
                transactions_list.sort(key=lambda x: x.get('date', ''))
                
                # Create DataFrame for display
                df_transactions = []
                running_balance = 0
                total_debit = 0
                total_credit = 0
                
                for transaction in transactions_list:
                    debit = float(transaction.get('debit', 0))
                    credit = float(transaction.get('credit', 0))
                    running_balance += credit - debit
                    total_debit += debit
                    total_credit += credit
                    
                    df_transactions.append({
                        "ID": transaction.get('id', ''),
                        "Date": format_date(transaction.get('date', '')),
                        "Particulars": transaction.get('particular', ''),
                        "Debit": format_currency(debit) if debit > 0 else "",
                        "Credit": format_currency(credit) if credit > 0 else "",
                        "Balance": format_currency(running_balance)
                    })
                
                # Add totals row
                df_transactions.append({
                    "ID": "",
                    "Date": "",
                    "Particulars": "TOTAL",
                    "Debit": format_currency(total_debit),
                    "Credit": format_currency(total_credit),
                    "Balance": format_currency(running_balance)
                })
                
                df = pd.DataFrame(df_transactions)
                st.dataframe(df.set_index("ID"), use_container_width=True)
                
                # Export to Excel
                if st.button("📥 Export Ledger to Excel", key=f"export_supplier_{supplier_id}"):
                    # Create a more detailed DataFrame for export
                    export_df = pd.DataFrame([
                        {
                            "Date": t.get('date', ''),
                            "Particulars": t.get('particular', ''),
                            "Debit": float(t.get('debit', 0)),
                            "Credit": float(t.get('credit', 0))
                        } for t in transactions_list
                    ])
                    
                    # Calculate running balance
                    balance = 0
                    balances = []
                    for _, row in export_df.iterrows():
                        balance += row['Credit'] - row['Debit']
                        balances.append(balance)
                    
                    export_df['Balance'] = balances
                    
                    # Add totals row
                    export_df.loc[len(export_df)] = [
                        "", "TOTAL", 
                        export_df['Debit'].sum(), 
                        export_df['Credit'].sum(), 
                        balance
                    ]
                    
                    # Save to Excel using Streamlit download button
                    filename = f"supplier_ledger_{supplier.get('name', 'unknown').replace(' ', '_')}.xlsx"
                    save_excel_file(export_df, filename)
                
                # Transaction actions
                st.subheader("⚙️ Transaction Actions")
                
                if len(transactions_list) > 0:
                    selected_transaction_id = st.selectbox(
                        "Select transaction",
                        options=[t.get('id', '') for t in transactions_list if t.get('id', '')],
                        format_func=lambda x: next((f"{t.get('date', '')} - {t.get('particular', '')}" for t in transactions_list if t.get('id', '') == x), ""),
                        key="supplier_transaction_select"
                    )
                    
                    if selected_transaction_id:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✏️ Edit Transaction", key=f"edit_supplier_trans_{selected_transaction_id}"):
                                st.session_state.edit_transaction = {
                                    'id': selected_transaction_id,
                                    'entity_type': 'supplier',
                                    'entity_id': supplier_id
                                }
                        with col2:
                            if st.button("🗑️ Delete Transaction", key=f"delete_supplier_trans_{selected_transaction_id}"):
                                if delete_transaction("supplier", supplier_id, selected_transaction_id):
                                    st.success("Transaction deleted successfully!")
                                    st.rerun()
            
            # Edit transaction form
            if (st.session_state.edit_transaction and 
                st.session_state.edit_transaction['entity_type'] == 'supplier' and 
                st.session_state.edit_transaction['entity_id'] == supplier_id):
                
                transaction_id = st.session_state.edit_transaction['id']
                transaction = transactions.get(transaction_id, {})
                
                if transaction:
                    with st.form(f"edit_supplier_transaction_form_{transaction_id}"):
                        st.subheader("✏️ Edit Transaction")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            try:
                                current_date = datetime.datetime.strptime(transaction.get('date', ''), '%Y-%m-%d').date()
                            except:
                                current_date = datetime.datetime.now().date()
                            
                            edit_date = st.date_input(
                                "Date*",
                                value=current_date,
                                key=f"edit_supplier_date_{transaction_id}"
                            )
                            
                            edit_particular = st.text_area(
                                "Particulars*", 
                                value=transaction.get('particular', ''),
                                help="Description of the transaction",
                                key=f"edit_supplier_particular_{transaction_id}"
                            )
                        
                        with col2:
                            edit_debit = st.number_input(
                                "Debit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('debit', 0)),
                                format="%.2f",
                                help="Amount you pay to supplier",
                                key=f"edit_supplier_debit_{transaction_id}"
                            )
                            
                            edit_credit = st.number_input(
                                "Credit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('credit', 0)),
                                format="%.2f",
                                help="Amount you owe to supplier",
                                key=f"edit_supplier_credit_{transaction_id}"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            update_trans_submitted = st.form_submit_button("Update Transaction")
                        
                        with col2:
                            cancel_trans = st.form_submit_button("Cancel")
                        
                        if update_trans_submitted:
                            if not edit_particular:
                                st.error("Particulars are required!")
                            elif edit_debit == 0 and edit_credit == 0:
                                st.error("Either Debit or Credit amount must be greater than zero!")
                            else:
                                updated_transaction = {
                                    'date': str(edit_date),
                                    'particular': edit_particular,
                                    'debit': str(edit_debit),
                                    'credit': str(edit_credit)
                                }
                                
                                if save_transaction("supplier", supplier_id, transaction_id, updated_transaction):
                                    st.success("Transaction updated successfully!")
                                    st.session_state.edit_transaction = None
                                    st.rerun()
                        
                        if cancel_trans:
                            st.session_state.edit_transaction = None
                            st.rerun()

# Settings Tab
with tab4:
    st.header("⚙️ Settings")
    
    # Create tabs for different settings categories
    settings_tab1, settings_tab2, settings_tab3 = st.tabs(["🔧 General", "🎨 Appearance", "💾 Data Management"])
    
    # General Settings
    with settings_tab1:
        st.subheader("🔧 General Settings")
        
        with st.form("general_settings_form"):
            currency_symbol = st.text_input(
                "Currency Symbol", 
                value=st.session_state.settings.get("currency_symbol", "₹"),
                help="Symbol to use for currency display"
            )
            
            date_format_options = {
                "%Y-%m-%d": "YYYY-MM-DD (e.g., 2023-01-31)",
                "%d/%m/%Y": "DD/MM/YYYY (e.g., 31/01/2023)",
                "%m/%d/%Y": "MM/DD/YYYY (e.g., 01/31/2023)",
                "%d-%m-%Y": "DD-MM-YYYY (e.g., 31-01-2023)",
                "%d %b %Y": "DD MMM YYYY (e.g., 31 Jan 2023)"
            }
            
            date_format = st.selectbox(
                "Date Display Format",
                options=list(date_format_options.keys()),
                format_func=lambda x: date_format_options[x],
                index=list(date_format_options.keys()).index(
                    st.session_state.settings.get("date_format", "%Y-%m-%d")
                )
            )
            
            auto_calculate_balance = st.checkbox(
                "Auto-calculate balance",
                value=st.session_state.settings.get("auto_calculate_balance", True),
                help="Automatically calculate running balance for transactions"
            )
            
            notification_enabled = st.checkbox(
                "Enable notifications",
                value=st.session_state.settings.get("notification_enabled", True),
                help="Show success/error notifications"
            )
            
            submitted = st.form_submit_button("💾 Save General Settings")
            
            if submitted:
                # Update settings
                st.session_state.settings.update({
                    "currency_symbol": currency_symbol,
                    "date_format": date_format,
                    "auto_calculate_balance": auto_calculate_balance,
                    "notification_enabled": notification_enabled
                })
                
                # Save to storage
                if save_settings(st.session_state.settings):
                    st.success("General settings saved successfully!")
    
    # Appearance Settings
    with settings_tab2:
        st.subheader("🎨 Appearance Settings")
        st.info("🌙 Dark theme is currently active and provides the best user experience.")
        
        with st.form("appearance_settings_form"):
            theme = st.radio(
                "Application Theme",
                options=["dark", "light"],
                index=0 if st.session_state.settings.get("theme", "dark") == "dark" else 1,
                help="Choose between dark or light theme"
            )
            
            submitted = st.form_submit_button("💾 Save Appearance Settings")
            
            if submitted:
                # Update settings
                st.session_state.settings["theme"] = theme
                
                # Save to storage
                if save_settings(st.session_state.settings):
                    st.success("Appearance settings saved successfully!")
                    st.rerun()
    
    # Data Management Settings
    with settings_tab3:
        st.subheader("💾 Data Management")
        
        # Backup data
        st.write("### 📤 Backup Data")
        st.write("Create a backup of all your data that you can restore later.")
        
        if st.button("📤 Create Backup"):
            try:
                # Load all data
                all_customers = load_customers()
                all_suppliers = load_suppliers()
                
                # Create backup data structure
                backup_data = {
                    "customers": all_customers,
                    "suppliers": all_suppliers,
                    "settings": st.session_state.settings,
                    "customer_transactions": {},
                    "supplier_transactions": {},
                    "backup_date": datetime.datetime.now().isoformat(),
                    "version": "1.0"
                }
                
                # Add transactions
                for customer_id in all_customers:
                    backup_data["customer_transactions"][customer_id] = load_transactions("customer", customer_id)
                
                for supplier_id in all_suppliers:
                    backup_data["supplier_transactions"][supplier_id] = load_transactions("supplier", supplier_id)
                
                # Convert to JSON
                backup_json = json.dumps(backup_data, indent=2)
                
                # Create download button
                filename = f"ledger_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                st.download_button(
                    label="📥 Download Backup File",
                    data=backup_json,
                    file_name=filename,
                    mime="application/json"
                )
                
                st.success("✅ Backup created successfully! Click the button above to download.")
            except Exception as e:
                st.error(f"❌ Error creating backup: {e}")
        
        # Restore data
        st.write("### 📥 Restore Data")
        st.write("Restore data from a previously created backup file.")
        st.warning("⚠️ This will overwrite your current data. Make sure to create a backup first.")
        
        uploaded_file = st.file_uploader("📁 Upload backup file", type=["json"])
        
        if uploaded_file is not None:
            if st.button("📥 Restore Data"):
                try:
                    # Load backup data
                    backup_data = json.loads(uploaded_file.getvalue().decode())
                    
                    # Validate backup data structure
                    required_keys = ["customers", "suppliers", "settings", "customer_transactions", "supplier_transactions"]
                    if not all(key in backup_data for key in required_keys):
                        st.error("❌ Invalid backup file format. Missing required data.")
                        st.stop()
                    
                    # Restore settings
                    st.session_state.settings = backup_data["settings"]
                    save_settings(backup_data["settings"])
                    
                    # Restore customers and their transactions
                    for customer_id, customer in backup_data["customers"].items():
                        save_customer(customer_id, customer)
                        
                        # Restore customer transactions
                        if customer_id in backup_data["customer_transactions"]:
                            for trans_id, transaction in backup_data["customer_transactions"][customer_id].items():
                                save_transaction("customer", customer_id, trans_id, transaction)
                    
                    # Restore suppliers and their transactions
                    for supplier_id, supplier in backup_data["suppliers"].items():
                        save_supplier(supplier_id, supplier)
                        
                        # Restore supplier transactions
                        if supplier_id in backup_data["supplier_transactions"]:
                            for trans_id, transaction in backup_data["supplier_transactions"][supplier_id].items():
                                save_transaction("supplier", supplier_id, trans_id, transaction)
                    
                    st.success("✅ Data restored successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error restoring data: {e}")
        
        # Reset data
        st.write("### 🗑️ Reset Data")
        st.write("Reset all data to start fresh. This will delete all customers, suppliers, and transactions.")
        st.error("⚠️ This action cannot be undone. Make sure to create a backup first.")
        
        reset_confirm = st.text_input("Type 'CONFIRM' to reset all data", key="reset_confirm")
        
        if st.button("🗑️ Reset All Data") and reset_confirm == "CONFIRM":
            try:
                # Reset local data
                if os.path.exists(DATA_DIR):
                    import shutil
                    shutil.rmtree(DATA_DIR)
                    os.makedirs(DATA_DIR, exist_ok=True)
                    os.makedirs(CUSTOMER_TRANSACTIONS_DIR, exist_ok=True)
                    os.makedirs(SUPPLIER_TRANSACTIONS_DIR, exist_ok=True)
                
                # Reset session state
                st.session_state.current_customer = None
                st.session_state.current_supplier = None
                st.session_state.edit_customer = None
                st.session_state.edit_supplier = None
                st.session_state.edit_transaction = None
                st.session_state.confirm_delete_customer = None
                st.session_state.confirm_delete_supplier = None
                
                st.success("✅ All data has been reset successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error resetting data: {e}")
        
        # Data statistics
        st.write("### 📊 Data Statistics")
        try:
            customers_count = len(load_customers())
            suppliers_count = len(load_suppliers())
            
            # Count total transactions
            total_customer_transactions = 0
            total_supplier_transactions = 0
            
            for customer_id in load_customers():
                customer_trans = load_transactions("customer", customer_id)
                total_customer_transactions += len(customer_trans)
            
            for supplier_id in load_suppliers():
                supplier_trans = load_transactions("supplier", supplier_id)
                total_supplier_transactions += len(supplier_trans)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Customers", customers_count)
            
            with col2:
                st.metric("🏢 Suppliers", suppliers_count)
            
            with col3:
                st.metric("📝 Customer Transactions", total_customer_transactions)
            
            with col4:
                st.metric("📝 Supplier Transactions", total_supplier_transactions)
                
        except Exception as e:
            st.error(f"Error loading statistics: {e}")

# Add a footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p><strong>📒 Ledger Management System</strong> | Version 2.0</p>
    <p>💾 Local Storage | 🌙 Dark Theme | 📱 Responsive Design</p>
    <p>© 2024 All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)

# Auto-save notification
if st.session_state.settings.get("notification_enabled", True):
    # Show a small notification about auto-save
    st.sidebar.markdown("---")
    st.sidebar.markdown("💡 **Tips:**")
    st.sidebar.markdown("• Data is automatically saved")
    st.sidebar.markdown("• Use backup feature regularly")
    st.sidebar.markdown("• Export ledgers to Excel")
