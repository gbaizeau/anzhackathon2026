import streamlit as st
import pandas as pd
import time
import requests

# Set up page config
st.set_page_config(page_title="Kroger Supplier Onboarding", page_icon="🛒")

# --- HEADER LOGOS ---
# Create two columns to push the logos to opposite sides
col1, col2 = st.columns(2)

with col1:
    # Kroger Logo (Left aligned automatically)
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS2wAZOzqwlQiRXdCY4ziKoirVvgKpt6wbnWw&s", width=200)

with col2:
    # Salsify Logo (Right aligned using HTML/CSS)
    st.markdown(
        "<div style='text-align: right;'><img src='https://www.salsify.com/hubfs/2023/Logos/Full%20Logo%20-%20Blue.svg' width='200'></div>", 
        unsafe_allow_html=True
    )

st.title("🛒 Supplier Data Onboarding Portal")
st.subheader("Validate your product feed before Salsify ingestion")

# --- 1. DEFINE ALLOWED TOKENS & SALSIFY TEMPLATE REQUIREMENTS ---
ALLOWED_TOKENS = [
    "GREG", 
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
            
        # Strip invisible spaces from column headers
        df.columns = df.columns.str.strip()
        
        st.markdown("### 🔍 Step 1: Previewing Uploaded Data")
        st.dataframe(df.head(5), use_container_width=True)
        
        # VALIDATION ENGINE
        errors = []
        is_valid = True
        
        st.markdown("### 🛠️ Step 2: Running Salsify Validation Checks")
        
        # Check A: Missing Columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            missing_str = ", ".join(missing_cols)
            errors.append(f"**Missing Columns:** Your file is missing required Salsify headers: `{missing_str}` *(Note: Check for spelling, it must be exact)*")
            is_valid = False
            
        if not missing_cols:
            # Force SKU to be a string and strip any rogue '.0' decimals from Excel
            df["SKU"] = df["SKU"].astype(str).str.replace(r'\.0$', '', regex=True)

            # Check B: Missing SKUs
            missing_skus = df["SKU"].isin(['nan', 'None', '']).sum()
            if missing_skus > 0:
                errors.append(f"**Missing Data:** Found {missing_skus} row(s) missing a `SKU` value.")
                is_valid = False
                
            # Check C: Flexible Price Validation & Cleaning
            original_nulls = df["Price"].isnull()
            cleaned_price_strings = df["Price"].astype(str).str.replace(r'[^\d.]', '', regex=True)
            clean_prices = pd.to_numeric(cleaned_price_strings, errors='coerce')
            
            if clean_prices.isnull().sum() > original_nulls.sum():
                errors.append("**Data Type Error:** The `Price` column contains text that cannot be converted to a pure number.")
                is_valid = False
            else:
                df["Price"] = clean_prices
                
            # Check D: Brand Validation
            df["Brand"] = df["Brand"].astype(str).str.strip()
            invalid_rows = df[~df["Brand"].isin(APPROVED_BRANDS) & df["Brand"].notnull() & (df["Brand"] != 'nan')]
            if not invalid_rows.empty:
                bad_brands = invalid_rows["Brand"].unique()
                bad_brands_str = ", ".join(map(str, bad_brands))
                errors.append(f"**Invalid Brand Name:** Found unapproved brands: `{bad_brands_str}`. Allowed Salsify list: {APPROVED_BRANDS}")
                is_valid = False

            # Check E: Main Image is a valid URL
            df["Main Image"] = df["Main Image"].astype(str).str.strip()
            invalid_urls = df[~df["Main Image"].str.startswith(('http://', 'https://'), na=False) & df["Main Image"].notnull() & (df["Main Image"] != 'nan')]
            if not invalid_urls.empty:
                errors.append("**Invalid Image URL:** The `Main Image` column must contain a valid public link starting with `http://` or `https://`.")
                is_valid = False

        # SHOW RESULTS TO SUPPLIER
        if not is_valid:
            st.error("❌ Validation Failed! Please fix the errors below and re-upload.")
            for err in errors:
                st.markdown(err)
        else:
            st.success("✅ Validation Passed! Your file matches the Salsify PXM template perfectly.")
            
            # --- 4. THE REAL API HANDOFF ---
            if st.button("🚀 Push Clean Data to Salsify"):
                with st.spinner("Authenticating and pushing to Salsify..."):
                    
                    # Salsify Configuration
                    org_id = "s-ed0a6d00-4fff-4c27-9a21-3a511984007d"
                    salsify_url = f"https://app.salsify.com/api/v1/orgs/{org_id}/products"
                    salsify_token = "ZDIYg45PzejWjHR-6TfpUTfQM8FfirbrD5ukT1ajzGY"
                    
                    headers = {
                        "Authorization": f"Bearer {salsify_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    # Convert the Pandas dataframe into a list of dictionaries
                    products = df.to_dict(orient='records')
                    success_count = 0
                    error_messages = []
                    
                    # Loop through each row and POST to Salsify
                    for product in products:
                        
                        # Map the strictly-formatted string SKU to the required Salsify 'Record ID'
                        product["Record ID"] = product["SKU"]
                        
                        # Clean up the payload before sending it to Salsify
                        product.pop("SKU", None)         # Remove SKU since it's mapped to Record ID
                        product.pop("Main Image", None)  # Remove URL to prevent digital asset property errors
                        
                        try:
                            response = requests.post(salsify_url, headers=headers, json=product)
                            
                            if response.status_code in [200, 201, 202, 204]: 
                                success_count += 1
                            else:
                                error_messages.append(f"SKU {product.get('Record ID')}: {response.status_code} - {response.text}")
                                
                        except Exception as e:
                            error_messages.append(f"SKU {product.get('Record ID')}: Connection failed - {e}")
                    
                    # Report results back to the user
                    if success_count == len(products):
                        st.balloons()
                        st.success(f"Boom! {success_count} products successfully ingested into Salsify.")
                    else:
                        st.warning(f"{success_count} out of {len(products)} products were ingested.")
                        if error_messages:
                            st.error("The following errors occurred during API transmission:")
                            for err in error_messages:
                                st.markdown(f"- {err}")
