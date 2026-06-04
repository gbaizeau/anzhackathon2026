import streamlit as st
import pandas as pd
import time
import requests

# Set up page config
st.set_page_config(page_title="Kroger Supplier Onboarding", page_icon="🛒")

# --- KROGER LOGO (Fixed using HTML so it bypasses Streamlit download blocks) ---
st.markdown("<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Kroger_logo_%282019%29.svg/500px-Kroger_logo_%282019%29.svg.png' width='200'>", unsafe_allow_html=True)

st.title("🛒 Supplier Data Onboarding Portal")
st.subheader("Validate your product feed before Salsify ingestion")

# --- 1. DEFINE ALLOWED TOKENS & SALSIFY TEMPLATE REQUIREMENTS ---
ALLOWED_TOKENS = [
    "KROGER-2026-ALPHA",
    "KROGER-2026-BETA",
    "KROGER-2026-GAMMA",
    "KROGER-2026-DELTA",
    "KROGER-2026-EPSILON"
]

REQUIRED_COLUMNS = ["SKU", "Product_Name", "Price", "Brand"]
APPROVED_BRANDS = ["Nike", "Adidas", "Puma", "Reebok", "Kroger"]

# --- 2. AUTHENTICATION (TOKEN VALIDATION) ---
# Initialize session state so the app remembers the user is logged in
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# The Login Gate
if not st.session_state["authenticated"]:
    st.info("🔒 Please enter your Supplier Access Token to continue.")
    token_input = st.text_input("Access Token", type="password")
    
    if st.button("Verify Token"):
        if token_input in ALLOWED_TOKENS:
            st.session_state["authenticated"] = True
            st.success("✅ Token verified! Access granted.")
            st.rerun()  # Refreshes the page to show the hidden UI
        else:
            # Updated error message
            st.error("❌ Your access token is invalid. Please contact Salsify Support.")

# --- 3. MAIN APP (ONLY SHOWS IF AUTHENTICATED) ---
if st.session_state["authenticated"]:
    
    # Add a logout button for testing convenience
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.markdown("---")
    
    # FILE UPLOADER UI
    uploaded_file = st.file_uploader("Drag and drop your supplier CSV file here", type=["csv"])

    if uploaded_file is not None:
        # Read the file
        df = pd.read_csv(uploaded_file)
        
        st.markdown("### 🔍 Step 1: Previewing Uploaded Data")
        st.dataframe(df.head(5), use_container_width=True)
        
        # VALIDATION ENGINE
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

        # SHOW RESULTS TO SUPPLIER
        if not is_valid:
            st.error("❌ Validation Failed! Please fix the errors below and re-upload.")
            for err in errors:
                st.markdown(err)
        else:
            st.success("✅ Validation Passed! Your file matches the Salsify PXM template perfectly.")
            
            # THE REAL API HANDOFF
            if st.button("🚀 Push Clean Data to Salsify"):
                with st.spinner("Authenticating and pushing to Salsify..."):
                    
                    # Convert the Pandas dataframe into a JSON payload
                    payload = df.to_dict(orient='records')
                    
                    # NOTE: We will update this block in the next step when you provide the token!
                    salsify_url = "https://app.salsify.com/api/v1/products" 
                    salsify_token = "YOUR_SALSIFY_TOKEN_HERE" 
                    
                    headers = {
                        "Authorization": f"Bearer {salsify_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    try:
                        response = requests.post(salsify_url, headers=headers, json=payload)
                        
                        if response.status_code in [200, 201, 202, 204]: 
                            st.balloons()
                            st.success("Boom! Data successfully ingested into Salsify via API.")
                        else:
                            st.error(f"Salsify API Error ({response.status_code}): {response.text}")
                            
                    except Exception as e:
                        st.error(f"Failed to connect to the API: {e}")
