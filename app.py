import streamlit as st
import pandas as pd
import time
import requests

# Set up page config
st.set_page_config(page_title="Kroger Supplier Onboarding", page_icon="🛒")

# --- KROGER LOGO (Updated to static Google image link) ---
st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS2wAZOzqwlQiRXdCY4ziKoirVvgKpt6wbnWw&s", width=200)

st.title("🛒 Supplier Data Onboarding Portal")
st.subheader("Validate your product feed before Salsify ingestion")

# --- 1. DEFINE ALLOWED TOKENS & SALSIFY TEMPLATE REQUIREMENTS ---
ALLOWED_TOKENS = [
    "GREG", # Fast-access token
    "KROGER-2026-ALPHA",
    "KROGER-2026-BETA",
    "KROGER-2026-GAMMA",
    "KROGER-2026-DELTA",
    "KROGER-2026-EPSILON"
]

REQUIRED_COLUMNS = ["SKU", "Product_Name", "Price", "Brand", "Main Image"]
APPROVED_BRANDS = ["Nike", "Adidas", "Puma", "Reebok", "Kroger"]

# --- 2. AUTHENTICATION (TOKEN VALIDATION) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.info("🔒 Please enter your Supplier Access Token to continue.")
    token_input = st.text_input("Access Token", type="password")
    
    if st.button("Verify Token"):
        if token_input in ALLOWED_TOKENS:
            st.session_state["authenticated"] = True
            st.success("✅ Token verified! Access granted.")
            st.rerun()
        else:
            st.error("❌ Your access token is invalid. Please contact Salsify Support.")

# --- 3. MAIN APP (ONLY SHOWS IF AUTHENTICATED) ---
if st.session_state["authenticated"]:
    
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.markdown("---")
    
    # FILE UPLOADER UI 
    uploaded_file = st.file_uploader("Drag and drop your supplier CSV or Excel file here", type=["csv", "xlsx"])

    if uploaded_file is not None:
        
        # Read the file based on its extension
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        
        st.markdown("### 🔍 Step 1: Previewing Uploaded Data")
        st.dataframe(df.head(5), use_container_width=True)
        
        # VALIDATION ENGINE
        errors = []
        is_valid = True
        
        st.markdown("### 🛠️ Step 2: Running Salsify Validation Checks")
        
        # Check A: Missing Columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            errors.append(f"**Missing Columns:** Your file is missing required Salsify headers: `{', '.join(
