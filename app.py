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
            # FIXED SYNTAX ERROR: Pulled the join string creation out of the f-string
            missing_str = ", ".join(missing_cols)
            errors.append(f"**Missing Columns:** Your file is missing required Salsify headers: `{missing_str}`")
            is_valid = False
            
        if not missing_cols:
            # Check B: Missing SKUs
            missing_skus = df["SKU"].isnull().sum()
            if missing_skus > 0:
                errors.append(f"**Missing Data:** Found {missing_skus} row(s) missing a `SKU` value.")
                is_valid = False
                
            # Check C: Price is a number
            clean_prices = pd.to_numeric(df["Price"], errors='coerce')
            if clean_prices.isnull().sum() > df["Price"].isnull().sum():
                errors.append("**Data Type Error:** The `Price` column contains letters or symbols. It must be numbers only.")
                is_valid = False
                
            # Check D: Brand Validation
            invalid_rows = df[~df["Brand"].isin(APPROVED_BRANDS) & df["Brand"].notnull()]
            if not invalid_rows.empty:
                bad_brands = invalid_rows["Brand"].unique()
                # FIXED SYNTAX ERROR: Pulled the join string creation out of the f-string
                bad_brands_str = ", ".join(map(str, bad_brands))
                errors.append(f"**Invalid Brand Name:** Found unapproved brands: `{bad_brands_str}`. Allowed Salsify list: {APPROVED_BRANDS}")
                is_valid = False

            # Check E: Main Image is a valid URL
            invalid_urls = df[~df["Main Image"].astype(str).str.startswith(('http://', 'https://'), na=False) & df["Main Image"].notnull()]
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
                        try:
                            response = requests.post(salsify_url, headers=headers, json=product)
                            
                            # 200, 201, 202, 204 are successful HTTP codes
                            if response.status_code in [200, 201, 202, 204]: 
                                success_count += 1
                            else:
                                error_messages.append(f"SKU {product.get('SKU')}: {response.status_code} - {response.text}")
                                
                        except Exception as e:
                            error_messages.append(f"SKU {product.get('SKU')}: Connection failed - {e}")
                    
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
