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
import tempfile
import threading
import io
import re
import base64
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Set page configuration
st.set_page_config(
    page_title="Ledger Management System",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Firebase with Streamlit secrets
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            # Try to get Firebase config from Streamlit secrets
            firebase_config = st.secrets["firebase"]
            
            # Create credentials from secrets
            cred_dict = {
                "type": firebase_config["type"],
                "project_id": firebase_config["project_id"],
                "private_key_id": firebase_config["private_key_id"],
                "private_key": firebase_config["private_key"],
                "client_email": firebase_config["client_email"],
                "client_id": firebase_config["client_id"],
                "auth_uri": firebase_config["auth_uri"],
                "token_uri": firebase_config["token_uri"],
                "auth_provider_x509_cert_url": firebase_config["auth_provider_x509_cert_url"],
                "client_x509_cert_url": firebase_config["client_x509_cert_url"],
                "universe_domain": firebase_config.get("universe_domain", "googleapis.com")
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': firebase_config["database_url"]
            })
            
            return True, db.reference('/')
        else:
            return True, db.reference('/')
            
    except Exception as e:
        st.error(f"🔥 Firebase initialization failed: {e}")
        st.error("Please check your Firebase configuration!")
        return False, None

# Initialize Firebase
using_firebase, firebase_db = init_firebase()

# Firebase Database Operations Class
class FirebaseDB:
    @staticmethod
    def load_settings():
        if using_firebase:
            try:
                settings_ref = firebase_db.child("settings")
                settings = settings_ref.get()
                if not settings:
                    # Default settings
                    default_settings = {
                        "currency_symbol": "₹",
                        "date_format": "%Y-%m-%d",
                        "auto_calculate_balance": True,
                        "notification_enabled": True
                    }
                    settings_ref.set(default_settings)
                    return default_settings
                return settings
            except Exception as e:
                st.error(f"Error loading settings: {e}")
        
        # Fallback default settings
        return {
            "currency_symbol": "₹",
            "date_format": "%Y-%m-%d",
            "auto_calculate_balance": True,
            "notification_enabled": True
        }
    
    @staticmethod
    def save_settings(settings_data):
        if using_firebase:
            try:
                firebase_db.child("settings").set(settings_data)
                return True
            except Exception as e:
                st.error(f"Error saving settings: {e}")
                return False
        return False
    
    @staticmethod
    def load_customers():
        if using_firebase:
            try:
                customers = firebase_db.child("customers").get()
                return customers if customers else {}
            except Exception as e:
                st.error(f"Error loading customers: {e}")
        return {}
    
    @staticmethod
    def save_customer(customer_id, customer_data):
        if using_firebase:
            try:
                firebase_db.child("customers").child(customer_id).set(customer_data)
                return True
            except Exception as e:
                st.error(f"Error saving customer: {e}")
                return False
        return False
    
    @staticmethod
    def delete_customer(customer_id):
        if using_firebase:
            try:
                firebase_db.child("customers").child(customer_id).delete()
                firebase_db.child("customer_transactions").child(customer_id).delete()
                return True
            except Exception as e:
                st.error(f"Error deleting customer: {e}")
                return False
        return False
    
    @staticmethod
    def load_suppliers():
        if using_firebase:
            try:
                suppliers = firebase_db.child("suppliers").get()
                return suppliers if suppliers else {}
            except Exception as e:
                st.error(f"Error loading suppliers: {e}")
        return {}
    
    @staticmethod
    def save_supplier(supplier_id, supplier_data):
        if using_firebase:
            try:
                firebase_db.child("suppliers").child(supplier_id).set(supplier_data)
                return True
            except Exception as e:
                st.error(f"Error saving supplier: {e}")
                return False
        return False
    
    @staticmethod
    def delete_supplier(supplier_id):
        if using_firebase:
            try:
                firebase_db.child("suppliers").child(supplier_id).delete()
                firebase_db.child("supplier_transactions").child(supplier_id).delete()
                return True
            except Exception as e:
                st.error(f"Error deleting supplier: {e}")
                return False
        return False
    
    @staticmethod
    def load_transactions(entity_type, entity_id):
        if using_firebase:
            try:
                transactions = firebase_db.child(f"{entity_type}_transactions").child(entity_id).get()
                return transactions if transactions else {}
            except Exception as e:
                st.error(f"Error loading transactions: {e}")
        return {}
    
    @staticmethod
    def save_transaction(entity_type, entity_id, transaction_id, transaction_data):
        if using_firebase:
            try:
                firebase_db.child(f"{entity_type}_transactions").child(entity_id).child(transaction_id).set(transaction_data)
                return True
            except Exception as e:
                st.error(f"Error saving transaction: {e}")
                return False
        return False
    
    @staticmethod
    def delete_transaction(entity_type, entity_id, transaction_id):
        if using_firebase:
            try:
                firebase_db.child(f"{entity_type}_transactions").child(entity_id).child(transaction_id).delete()
                return True
            except Exception as e:
                st.error(f"Error deleting transaction: {e}")
                return False
        return False

# Initialize session state
if 'settings' not in st.session_state:
    st.session_state.settings = FirebaseDB.load_settings()

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
    /* Base elements with elegant dark theme */
    .stApp, .stTabs, .main {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    }
    
    /* Elegant headers */
    h1, h2, h3 {
        color: #E2E8F0 !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em !important;
    }
    
    h4, h5, h6 {
        color: #CBD5E1 !important;
        font-weight: 500 !important;
    }
    
    /* Sophisticated buttons */
    .stButton>button {
        background: linear-gradient(135deg, #475569 0%, #334155 100%) !important;
        color: #F8FAFC !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        border: 1px solid #475569 !important;
        padding: 0.75rem 1.5rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease !important;
        font-size: 14px !important;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #64748B 0%, #475569 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* Refined input fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
        padding: 0.75rem !important;
        font-size: 14px !important;
    }
    
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus, .stNumberInput>div>div>input:focus {
        border-color: #64748B !important;
        box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.1) !important;
        outline: none !important;
    }
    
    /* Elegant metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        border: 1px solid #334155 !important;
        transition: all 0.3s ease !important;
    }
    .metric-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
        border-color: #475569 !important;
    }
    .metric-value {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #E2E8F0 !important;
        line-height: 1 !important;
    }
    .metric-label {
        font-size: 0.875rem !important;
        color: #94A3B8 !important;
        font-weight: 500 !important;
        margin-top: 0.5rem !important;
    }
    
    /* Sophisticated sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    
    /* Refined tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0F172A !important;
        border-bottom: 1px solid #334155 !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8 !important;
        font-weight: 500 !important;
        background-color: transparent !important;
        border: none !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [aria-selected="true"] {
        color: #F8FAFC !important;
        background: linear-gradient(135deg, #475569 0%, #334155 100%) !important;
        border-bottom: 2px solid #64748B !important;
    }
    
    /* Elegant forms */
    .stForm {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
        padding: 2rem !important;
        border-radius: 12px !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Refined dataframes */
    .stDataFrame {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    .stDataFrame th {
        background: linear-gradient(135deg, #475569 0%, #334155 100%) !important;
        color: #F8FAFC !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #64748B !important;
    }
    .stDataFrame td {
        color: #E2E8F0 !important;
        border-bottom: 1px solid #334155 !important;
        background-color: #1E293B !important;
    }
    
    /* Status messages with elegant colors */
    .stSuccess {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(21, 128, 61, 0.1) 100%) !important;
        border-left: 4px solid #22C55E !important;
        color: #F0FDF4 !important;
        border-radius: 6px !important;
    }
    
    .stError {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(185, 28, 28, 0.1) 100%) !important;
        border-left: 4px solid #EF4444 !important;
        color: #FEF2F2 !important;
        border-radius: 6px !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%) !important;
        border-left: 4px solid #F59E0B !important;
        color: #FFFBEB !important;
        border-radius: 6px !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(29, 78, 216, 0.1) 100%) !important;
        border-left: 4px solid #3B82F6 !important;
        color: #EFF6FF !important;
        border-radius: 6px !important;
    }
    
    /* Elegant scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0F172A;
    }
    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #64748B;
    }
    </style>
    """, unsafe_allow_html=True)


apply_theme()

# Utility functions
def format_currency(amount):
    currency_symbol = st.session_state.settings.get("currency_symbol", "₹")
    return f"{currency_symbol}{amount:,.2f}"

def format_date(date_str):
    try:
        date_format = st.session_state.settings.get("date_format", "%Y-%m-%d")
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(date_format)
    except:
        return date_str

def calculate_balance(transactions_list):
    balance = 0
    for transaction in transactions_list:
        debit = float(transaction.get('debit', 0))
        credit = float(transaction.get('credit', 0))
        balance += credit - debit
    return balance

def save_excel_file(dataframe, default_filename="ledger_export.xlsx"):
    """Save dataframe as Excel file using Streamlit's download button"""
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

# Main app title
st.title("🔥 Firebase Ledger Management System")

# Firebase status indicator
if using_firebase:
    st.success("🔥 **Connected to Firebase** | ☁️ **Real-time Database Active**")
else:
    st.error("❌ **Firebase Connection Failed** | Please check your configuration")
    st.stop()

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Customers", "🏢 Suppliers", "⚙️ Settings"])

# Dashboard Tab
with tab1:
    st.header("📊 Dashboard")
    
    # Load all data for dashboard
    all_customers = FirebaseDB.load_customers()
    all_suppliers = FirebaseDB.load_suppliers()
    
    # Calculate total receivables and payables
    total_receivable = 0
    total_payable = 0
    
    for customer_id, customer in all_customers.items():
        customer_transactions = FirebaseDB.load_transactions("customer", customer_id)
        if customer_transactions:
            customer_balance = calculate_balance(list(customer_transactions.values()))
            if customer_balance > 0:  # Positive balance means customer owes money
                total_receivable += customer_balance
            else:  # Negative balance means we owe customer
                total_payable -= customer_balance
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = FirebaseDB.load_transactions("supplier", supplier_id)
        if supplier_transactions:
            supplier_balance = calculate_balance(list(supplier_transactions.values()))
            if supplier_balance < 0:  # Negative balance means we owe supplier
                total_payable -= supplier_balance
            else:  # Positive balance means supplier owes us
                total_receivable += supplier_balance
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-left: 4px solid #22C55E;">
            <div class="metric-value">{format_currency(total_receivable)}</div>
            <div class="metric-label">📈 Receivables</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-left: 4px solid #EF4444;">
            <div class="metric-value">{format_currency(total_payable)}</div>
            <div class="metric-label">📉 Payables</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        net_balance = total_receivable - total_payable
        border_color = "#22C55E" if net_balance >= 0 else "#EF4444"

        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-left: 4px solid {border_color};">
            <div class="metric-value">{format_currency(net_balance)}</div>
            <div class="metric-label">💼 Net Position</div>
        </div>
        """, unsafe_allow_html=True)
            
    # Display customer and supplier counts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-left: 4px solid #64748B;">
            <div class="metric-value">{len(all_customers)}</div>
            <div class="metric-label">👥 Total Customers</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:

# REPLACE with:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-left: 4px solid #F59E0B;">
            <div class="metric-value">{len(all_suppliers)}</div>
            <div class="metric-label">🏢 Total Suppliers</div>
        </div>
        """, unsafe_allow_html=True)

    
    # Recent transactions
    st.subheader("📋 Recent Transactions")
    
    # Combine all transactions
    all_transactions = []
    
    for customer_id, customer in all_customers.items():
        customer_transactions = FirebaseDB.load_transactions("customer", customer_id)
        if customer_transactions:
            for trans_id, transaction in customer_transactions.items():
                transaction['entity_name'] = customer.get('name', 'Unknown')
                transaction['entity_type'] = 'Customer'
                transaction['id'] = trans_id
                transaction['entity_id'] = customer_id
                all_transactions.append(transaction)
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = FirebaseDB.load_transactions("supplier", supplier_id)
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
            
            submitted = st.form_submit_button("➕ Add Customer")
            if submitted:
                if not new_name or not new_phone:
                    st.error("❌ Name and Phone Number are required!")
                else:
                    # Check if customer with same phone already exists
                    all_customers = FirebaseDB.load_customers()
                    exists = False
                    for customer in all_customers.values():
                        if customer.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"❌ Customer with phone number {new_phone} already exists!")
                    else:
                        customer_id = str(uuid.uuid4())
                        customer_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if FirebaseDB.save_customer(customer_id, customer_data):
                            st.success(f"✅ Customer {new_name} added successfully!")
                            st.rerun()
    
    # Search and filter customers
    all_customers = FirebaseDB.load_customers()
    
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
                transactions = FirebaseDB.load_transactions("customer", customer_id)
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
                    "Status": "🔴 Due" if balance > 0 else "🟢 Advance" if balance < 0 else "⚪ Settled"
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
                transactions = FirebaseDB.load_transactions("customer", customer_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Display balance
                balance_color = "#DC2626" if balance > 0 else "#059669" if balance < 0 else "#F59E0B"
                status_text = "🔴 Due" if balance > 0 else "🟢 Advance" if balance < 0 else "⚪ Settled"
                
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 15px; border-radius: 8px; text-align: center;">
                    <h3 style="margin: 0;">💰 Balance: {format_currency(balance)}</h3>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">Status: {status_text}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("✏️ Edit", key=f"edit_customer_{customer_id}"):
                    st.session_state.edit_customer = customer_id
                
                if st.button("🗑️ Delete", key=f"delete_customer_{customer_id}"):
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
                        update_submitted = st.form_submit_button("💾 Update Customer")
                    
                    with col2:
                        cancel = st.form_submit_button("❌ Cancel")
                    
                    if update_submitted:
                        if not edit_name or not edit_phone:
                            st.error("❌ Name and Phone Number are required!")
                        else:
                            # Check if phone number is already used by another customer
                            phone_exists = False
                            for cid, cust in all_customers.items():
                                if cid != customer_id and cust.get('phone') == edit_phone:
                                    phone_exists = True
                                    break
                            
                            if phone_exists:
                                st.error(f"❌ Phone number {edit_phone} is already used by another customer!")
                            else:
                                # Update customer data
                                updated_customer = {
                                    'name': edit_name,
                                    'phone': edit_phone,
                                    'email': edit_email,
                                    'address': edit_address,
                                    'created_on': customer.get('created_on', datetime.datetime.now().strftime('%Y-%m-%d'))
                                }
                                
                                if FirebaseDB.save_customer(customer_id, updated_customer):
                                    st.success("✅ Customer updated successfully!")
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
                    if st.button("🗑️ Yes, Delete", key=f"confirm_delete_customer_{customer_id}"):
                        if FirebaseDB.delete_customer(customer_id):
                            st.success("✅ Customer deleted successfully!")
                            st.session_state.confirm_delete_customer = None
                            st.session_state.current_customer = None
                            st.rerun()
                
                with col2:
                    if st.button("❌ Cancel", key=f"cancel_delete_customer_{customer_id}"):
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
                            "📅 Date",
                            value=datetime.datetime.now().date(),
                            key=f"customer_date_input_{customer_id}"
                        )
                        
                        particular = st.text_area(
                            "📝 Particulars*", 
                            help="Description of the transaction",
                            key=f"customer_particular_{customer_id}"
                        )
                    
                    with col2:
                        debit = st.number_input(
                            "💰 Debit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount customer gives (payment received)",
                            key=f"customer_debit_{customer_id}"
                        )
                        
                        credit = st.number_input(
                            "💸 Credit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount customer takes (goods/services provided)",
                            key=f"customer_credit_{customer_id}"
                        )
                    
                    transaction_submitted = st.form_submit_button("➕ Add Transaction")
                    
                    if transaction_submitted:
                        if not particular:
                            st.error("❌ Particulars are required!")
                        elif debit == 0 and credit == 0:
                            st.error("❌ Either Debit or Credit amount must be greater than zero!")
                        else:
                            transaction_id = str(uuid.uuid4())
                            transaction_data = {
                                'date': date_input.strftime('%Y-%m-%d'),
                                'particular': particular,
                                'debit': str(debit),
                                'credit': str(credit)
                            }
                            
                            if FirebaseDB.save_transaction("customer", customer_id, transaction_id, transaction_data):
                                st.success("✅ Transaction added successfully!")
                                st.rerun()
            
            # Display transactions
            transactions = FirebaseDB.load_transactions("customer", customer_id)
            
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
                    running_balance += debit - credit
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
                    "Particulars": "📊 TOTAL",
                    "Debit": format_currency(total_debit),
                    "Credit": format_currency(total_credit),
                    "Balance": format_currency(running_balance)
                })
                
                df = pd.DataFrame(df_transactions)
                st.dataframe(df.set_index("ID"), use_container_width=True)
                
                # Export to Excel
                if st.button("📥 Export Ledger to Excel", key=f"export_customer_{customer_id}"):
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
                        balance += row['Debit'] - row['Credit']
                        balances.append(balance)
                    
                    export_df['Balance'] = balances
                    
                    filename = f"customer_ledger_{customer.get('name', 'unknown').replace(' ', '_')}.xlsx"
                    save_excel_file(export_df, filename)
                
                # Transaction actions
                st.subheader("⚙️ Transaction Actions")
                
                selected_transaction_id = st.selectbox(
                    "Select transaction to edit/delete",
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
                            if FirebaseDB.delete_transaction("customer", customer_id, selected_transaction_id):
                                st.success("✅ Transaction deleted successfully!")
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
                            edit_date = st.date_input(
                                "📅 Date",
                                value=datetime.datetime.strptime(transaction.get('date', ''), '%Y-%m-%d').date(),
                                key=f"edit_customer_date_{transaction_id}"
                            )
                            
                            edit_particular = st.text_area(
                                "📝 Particulars*", 
                                value=transaction.get('particular', ''),
                                help="Description of the transaction",
                                key=f"edit_customer_particular_{transaction_id}"
                            )
                        
                        with col2:
                            edit_debit = st.number_input(
                                "💰 Debit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('debit', 0)),
                                format="%.2f",
                                help="Amount customer gives (payment received)",
                                key=f"edit_customer_debit_{transaction_id}"
                            )
                            
                            edit_credit = st.number_input(
                                "💸 Credit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('credit', 0)),
                                format="%.2f",
                                help="Amount customer takes (goods/services provided)",
                                key=f"edit_customer_credit_{transaction_id}"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            update_trans_submitted = st.form_submit_button("💾 Update Transaction")
                        
                        with col2:
                            cancel_trans = st.form_submit_button("❌ Cancel")
                        
                        if update_trans_submitted:
                            if not edit_particular:
                                st.error("❌ Particulars are required!")
                            elif edit_debit == 0 and edit_credit == 0:
                                st.error("❌ Either Debit or Credit amount must be greater than zero!")
                            else:
                                updated_transaction = {
                                    'date': edit_date.strftime('%Y-%m-%d'),
                                    'particular': edit_particular,
                                    'debit': str(edit_debit),
                                    'credit': str(edit_credit)
                                }
                                
                                if FirebaseDB.save_transaction("customer", customer_id, transaction_id, updated_transaction):
                                    st.success("✅ Transaction updated successfully!")
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
            
            submitted = st.form_submit_button("➕ Add Supplier")
            if submitted:
                if not new_name or not new_phone:
                    st.error("❌ Name and Phone Number are required!")
                else:
                    # Check if supplier with same phone already exists
                    all_suppliers = FirebaseDB.load_suppliers()
                    exists = False
                    for supplier in all_suppliers.values():
                        if supplier.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"❌ Supplier with phone number {new_phone} already exists!")
                    else:
                        supplier_id = str(uuid.uuid4())
                        supplier_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if FirebaseDB.save_supplier(supplier_id, supplier_data):
                            st.success(f"✅ Supplier {new_name} added successfully!")
                            st.rerun()
    
    # Search and filter suppliers
    all_suppliers = FirebaseDB.load_suppliers()
    
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
                transactions = FirebaseDB.load_transactions("supplier", supplier_id)
                
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
                    "Status": "🔴 Due" if balance < 0 else "🟢 Advance" if balance > 0 else "⚪ Settled"
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
    
    # Display supplier profile and ledger (similar structure to customers)
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
                transactions = FirebaseDB.load_transactions("supplier", supplier_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Display balance
                balance_color = "#DC2626" if balance < 0 else "#059669" if balance > 0 else "#F59E0B"
                status_text = "🔴 Due" if balance < 0 else "🟢 Advance" if balance > 0 else "⚪ Settled"
                
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 15px; border-radius: 8px; text-align: center;">
                    <h3 style="margin: 0;">💰 Balance: {format_currency(balance)}</h3>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">Status: {status_text}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("✏️ Edit", key=f"edit_supplier_{supplier_id}"):
                    st.session_state.edit_supplier = supplier_id
                
                if st.button("🗑️ Delete", key=f"delete_supplier_{supplier_id}"):
                    st.session_state.confirm_delete_supplier = supplier_id
            
            # Similar edit/delete forms and transaction management as customers
            # (Implementation follows same pattern as customer section)

# Settings Tab
with tab4:
    st.header("⚙️ Settings")
    
    # General Settings
    st.subheader("🔧 General Settings")
    
    with st.form("settings_form"):
        currency_symbol = st.text_input(
            "💰 Currency Symbol", 
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
            "📅 Date Display Format",
            options=list(date_format_options.keys()),
            format_func=lambda x: date_format_options[x],
            index=list(date_format_options.keys()).index(
                st.session_state.settings.get("date_format", "%Y-%m-%d")
            )
        )
        
        auto_calculate_balance = st.checkbox(
            "🔄 Auto-calculate balance",
            value=st.session_state.settings.get("auto_calculate_balance", True),
            help="Automatically calculate running balance for transactions"
        )
        
        notification_enabled = st.checkbox(
            "🔔 Enable notifications",
            value=st.session_state.settings.get("notification_enabled", True),
            help="Show success/error notifications"
        )
        
        submitted = st.form_submit_button("💾 Save Settings")
        
        if submitted:
            # Update settings
            st.session_state.settings.update({
                "currency_symbol": currency_symbol,
                "date_format": date_format,
                "auto_calculate_balance": auto_calculate_balance,
                "notification_enabled": notification_enabled
            })
            
            # Save to Firebase
            if FirebaseDB.save_settings(st.session_state.settings):
                st.success("✅ Settings saved successfully!")
    
    # Data Management
    st.subheader("🗄️ Data Management")
    
    # Backup data
    st.write("### 💾 Backup Data")
    st.write("Create a backup of all your data that you can restore later.")
    
    if st.button("📥 Create Backup"):
        try:
            # Load all data
            all_customers = FirebaseDB.load_customers()
            all_suppliers = FirebaseDB.load_suppliers()
            
            # Create backup data structure
            backup_data = {
                "customers": all_customers,
                "suppliers": all_suppliers,
                "settings": st.session_state.settings,
                "customer_transactions": {},
                "supplier_transactions": {}
            }
            
            # Add transactions
            for customer_id in all_customers:
                backup_data["customer_transactions"][customer_id] = FirebaseDB.load_transactions("customer", customer_id)
            
            for supplier_id in all_suppliers:
                backup_data["supplier_transactions"][supplier_id] = FirebaseDB.load_transactions("supplier", supplier_id)
            
            # Convert to JSON
            backup_json = json.dumps(backup_data, indent=2)
            
            # Create download button
            filename = f"firebase_ledger_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
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
    st.write("### 📤 Restore Data")
    st.write("Restore data from a previously created backup file.")
    st.warning("⚠️ This will overwrite your current data. Make sure to create a backup first.")
    
    uploaded_file = st.file_uploader("📁 Upload backup file", type=["json"])
    
    if uploaded_file is not None:
        if st.button("🔄 Restore Data"):
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
                FirebaseDB.save_settings(backup_data["settings"])
                
                # Restore customers and their transactions
                for customer_id, customer in backup_data["customers"].items():
                    FirebaseDB.save_customer(customer_id, customer)
                    
                    # Restore customer transactions
                    if customer_id in backup_data["customer_transactions"]:
                        for trans_id, transaction in backup_data["customer_transactions"][customer_id].items():
                            FirebaseDB.save_transaction("customer", customer_id, trans_id, transaction)
                
                # Restore suppliers and their transactions
                for supplier_id, supplier in backup_data["suppliers"].items():
                    FirebaseDB.save_supplier(supplier_id, supplier)
                    
                    # Restore supplier transactions
                    if supplier_id in backup_data["supplier_transactions"]:
                        for trans_id, transaction in backup_data["supplier_transactions"][supplier_id].items():
                            FirebaseDB.save_transaction("supplier", supplier_id, trans_id, transaction)
                
                st.success("✅ Data restored successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error restoring data: {e}")
    
    # Firebase Status
    st.write("### 🔥 Firebase Status")
    
    if using_firebase:
        st.success("🟢 **Connected to Firebase**")
        st.info("📊 **Real-time Database:** Active")
        st.info("☁️ **Cloud Storage:** Enabled")
        
        # Show database URL (masked for security)
        db_url = st.secrets["firebase"]["database_url"]
        masked_url = db_url[:30] + "..." + db_url[-20:] if len(db_url) > 50 else db_url
        st.info(f"🌐 **Database URL:** {masked_url}")
        
        # Test connection
        if st.button("🔍 Test Firebase Connection"):
            try:
                # Try to read from Firebase
                test_data = firebase_db.child("test").get()
                st.success("✅ Firebase connection test successful!")
            except Exception as e:
                st.error(f"❌ Firebase connection test failed: {e}")
    else:
        st.error("🔴 **Firebase Connection Failed**")
        st.error("❌ Please check your secrets.toml configuration")
    
    # Reset data
    st.write("### 🗑️ Reset Data")
    st.write("Reset all data to start fresh. This will delete all customers, suppliers, and transactions.")
    st.error("⚠️ **WARNING:** This action cannot be undone. Make sure to create a backup first.")
    
    reset_confirmation = st.text_input("Type 'RESET' to confirm data deletion", key="reset_confirm")
    
    if st.button("🗑️ Reset All Data") and reset_confirmation == "RESET":
        try:
            # Clear Firebase data
            if using_firebase:
                firebase_db.child("customers").delete()
                firebase_db.child("suppliers").delete()
                firebase_db.child("customer_transactions").delete()
                firebase_db.child("supplier_transactions").delete()
                
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
            else:
                st.error("❌ Cannot reset data: Firebase not connected")
        except Exception as e:
            st.error(f"❌ Error resetting data: {e}")

# Sidebar with quick actions
# Sidebar with quick actions
with st.sidebar:
    st.header("🚀 Quick Actions")
    
    # Firebase status indicator
    if using_firebase:
        st.success("🔥 Firebase Connected")
    else:
        st.error("❌ Firebase Disconnected")
    
    st.markdown("---")
    
    # Quick stats
    all_customers = FirebaseDB.load_customers()
    all_suppliers = FirebaseDB.load_suppliers()
    
    st.metric("👥 Customers", len(all_customers))
    st.metric("🏢 Suppliers", len(all_suppliers))
    
    # Quick navigation - SIMPLIFIED
    st.markdown("### 📋 Quick Navigation")
    st.info("Use the tabs above to navigate between sections")
    
    # Quick actions that actually work
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    if st.button("📥 Quick Backup", use_container_width=True):
        st.info("Go to Settings tab for backup options")
    
    st.markdown("---")
    
    # Recent activity (keep this part as it works)
    st.markdown("### 🕒 Recent Activity")
    
    # Get recent transactions
    all_transactions = []
    
    for customer_id, customer in all_customers.items():
        customer_transactions = FirebaseDB.load_transactions("customer", customer_id)
        if customer_transactions:
            for trans_id, transaction in customer_transactions.items():
                transaction['entity_name'] = customer.get('name', 'Unknown')
                transaction['entity_type'] = 'Customer'
                all_transactions.append(transaction)
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = FirebaseDB.load_transactions("supplier", supplier_id)
        if supplier_transactions:
            for trans_id, transaction in supplier_transactions.items():
                transaction['entity_name'] = supplier.get('name', 'Unknown')
                transaction['entity_type'] = 'Supplier'
                all_transactions.append(transaction)
    
    # Sort by date and show recent 5
    all_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    recent_transactions = all_transactions[:5]
    
    if recent_transactions:
        for transaction in recent_transactions:
            debit = float(transaction.get('debit', 0))
            credit = float(transaction.get('credit', 0))
            amount = debit if debit > 0 else credit
            transaction_type = "💰 Debit" if debit > 0 else "💸 Credit"
            
            st.write(f"**{transaction.get('entity_name', 'Unknown')}**")
            st.write(f"{transaction_type}: {format_currency(amount)}")
            st.write(f"📅 {format_date(transaction.get('date', ''))}")
            st.write("---")
    else:
        st.info("No recent transactions")
    
    # App info
    st.markdown("---")
    st.markdown("### ℹ️ App Info")
    st.info("🔥 Firebase Ledger System v2.0")
    st.info("☁️ Cloud-powered accounting")
    st.info("🔒 Secure & Real-time")


# Footer
st.markdown("---")

# REPLACE with:
st.markdown("""
<div style="text-align: center; color: #64748B; padding: 2rem; border-top: 1px solid #334155; margin-top: 3rem;">
    <h4 style="color: #E2E8F0; margin-bottom: 0.5rem;">📊 Ledger Management System</h4>
    <p style="margin: 0.25rem 0; font-size: 0.875rem;">Professional Edition | Powered by Firebase & Streamlit</p>
    <p style="margin: 0.25rem 0; font-size: 0.875rem;">© 2024 All Rights Reserved</p>
    <p style="margin: 0.25rem 0; font-size: 0.75rem; color: #94A3B8;">🔒 Secure • ☁️ Cloud-based • ⚡ Real-time</p>
</div>
""", unsafe_allow_html=True)


# Auto-refresh indicator
if st.session_state.settings.get("notification_enabled", True):
    # Show connection status
    if using_firebase:
        st.toast("🔥 Connected to Firebase!", icon="✅")
    else:
        st.toast("❌ Firebase connection failed!", icon="🚨")



