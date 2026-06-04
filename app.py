import streamlit as st
import pandas as pd
import time

# Set up page config
st.set_page_config(page_title="Supplier Onboarding Portal", page_icon="📦")
st.title("📦 Supplier Data Onboarding Portal")
st.subheader("Validate your product feed before Salsify ingestion")

# --- 1. DEFINE SALSIFY TEMPLATE REQUIREMENTS ---
REQUIRED_COLUMNS = ["SKU", "Product_Name", "Price", "Brand"]
APPROVED_BRANDS = ["Nike", "Adidas", "Puma", "Reebok"]

# --- 2. FILE UPLOADER UI ---
uploaded_file = st.file_uploader("Drag and drop your supplier CSV file here", type=["csv"])

if uploaded_file is not None:
    # Read the file
    df = pd.read_csv(uploaded_file)
    
    st.markdown("### 🔍 Step 1: Previewing Uploaded Data")
    st.dataframe(df.head(5), use_container_width=True)
    
    # --- 3. VALIDATION ENGINE ---
    errors = []
    is_valid = True
    
    st.markdown("### 🛠️ Step 2: Running Salsify Validation Checks")
    
    # Check A: Missing Columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append(f"**Missing Columns:** Your file is missing required Salsify headers: `{', '.join(missing_cols)}`")
        is_valid = False
        
    # Run cell-level checks only if columns match
    if not missing_cols:
        # Check B: Missing SKUs (Empty cells)
        missing_skus = df["SKU"].isnull().sum()
        if missing_skus > 0:
            errors.append(f"**Missing Data:** Found {missing_skus} row(s) missing a `SKU` value.")
            is_valid = False
            
        # Check C: Price is a number
        # Coerce errors to NaN, if any NaN are generated where data originally existed, it means it wasn't a number
        clean_prices = pd.to_numeric(df["Price"], errors='coerce')
        if clean_prices.isnull().sum() > df["Price"].isnull().sum():
            errors.append("**Data Type Error:** The `Price` column contains letters or symbols. It must be numbers only.")
            is_valid = False
            
        # Check D: Brand Validation (Allowed List)
        invalid_rows = df[~df["Brand"].isin(APPROVED_BRANDS) & df["Brand"].notnull()]
        if not invalid_rows.empty:
            bad_brands = invalid_rows["Brand"].unique()
            errors.append(f"**Invalid Brand Name:** Found unapproved brands: `{', '.join(map(str, bad_brands))}`. Allowed Salsify list: {APPROVED_BRANDS}")
            is_valid = False

    # --- 4. SHOW RESULTS TO SUPPLIER ---
    if not is_valid:
        st.error("❌ Validation Failed! Please fix the errors below and re-upload.")
        for err in errors:
            st.markdown(err)
    else:
        st.success("✅ Validation Passed! Your file matches the Salsify PXM template perfectly.")
        
        # --- 5. THE HANDOFF (MOCKED FOR HACKATHON) ---
        if st.button("🚀 Push Clean Data to Salsify"):
            with st.spinner("Connecting to Salsify SFTP & streaming data..."):
                time.sleep(2) # Simulates network latency
                st.balloons()
                st.success("Success! Data successfully ingested into Salsify.")