import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Order P&L Analyzer", layout="wide", page_icon="📦")

st.title("📦 Aavoni Order-level P&L Analyzer")
st.markdown("Flipkart **Orders P&L** sheet ke base par calculation.")

# --- SIDEBAR: COST SETTINGS ---
with st.sidebar:
    st.header("📊 Cost Settings")
    std_base = st.number_input("Standard Pant Cost (PT/PL)", value=165)
    hf_base = st.number_input("HF Series Cost", value=110)
    st.divider()
    st.info(f"Cost Logic:\n- HF: {hf_base} (S) / {hf_base*2} (CBO)\n- Std: {std_base} (S) / {std_base*2} (CBO) / {std_base*3} (3CBO)")

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        excel_data = pd.ExcelFile(uploaded_file)
        
        # Orders P&L sheet ko dhoondna
        target_sheet = next((s for s in excel_data.sheet_names if "Orders P&L" in s), excel_data.sheet_names[0])
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        # Column names clean karna
        df.columns = [str(c).strip() for c in df.columns]
        
        # Orders sheet ke specific columns
        sku_col = "SKU Name"
        units_col = "Net Units"
        settlement_col = "Bank Settlement [Projected] (INR)"
        status_col = "Order Status"

        if sku_col in df.columns and settlement_col in df.columns:
            # Data Cleaning
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            # Settlement column ka projected value (kabhi-kabhi ye multiple columns mein hota hai, hum main projected uthayenge)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0)

            # --- CATEGORIZATION LOGIC ---
            def get_cat_and_cost(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                if "3CBO" in sku: return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            # Processing
            cat_results = df[sku_col].apply(get_cat_and_cost)
            df['Category'] = [x[0] for x in cat_results]
            df['Unit_Cost'] = [x[1] for x in cat_results]
            
            # Profit: Settlement - (Net Units * Cost)
            # Order level par agar Net Unit 1 hai toh cost minus hoga, agar 0 (return) hai toh cost 0 hoga.
            df['Net_Profit'] = df.apply(
                lambda x: x[settlement_col] - (x[units_col] * x['Unit_Cost']) if x[units_col] > 0 else x[settlement_col], 
                axis=1
            )

            # --- 1. SUMMARY METRICS ---
            t_pay = df[settlement_col].sum()
            t_prof = df['Net_Profit'].sum()
            t_units = df[units_col].sum()
            delivered_orders = df[df[status_col] == 'DELIVERED'].shape[0] if status_col in df.columns else "N/A"
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Settlement", f"₹{int(t_pay):,}")
            c2.metric("Net Profit", f"₹{int(t_prof):,}")
            c3.metric("Net Units Sold", f"{int(t_units)}")
            c4.metric("Delivered Orders", f"{delivered_orders}")

            # --- 2. CATEGORY ANALYSIS ---
            st.subheader("📊 Category-wise Performance")
            avg_df = df[df[units_col] > 0].groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            }).rename(columns={units_col: 'Total Units'})
            
            avg_df['Avg Profit/Unit'] = (avg_df['Net_Profit'] / avg_df['Total Units']).round(0).astype(int)
            st.table(avg_df)

            # --- 3. RECENT ORDERS BREAKDOWN ---
            st.subheader("🔎 Recent Orders Detail")
            cols_to_show = [sku_col, 'Category', status_col, units_col, settlement_col, 'Net_Profit']
            # Check if columns exist before showing
            available_cols = [c for c in cols_to_show if c in df.columns or c in ['Category', 'Net_Profit']]
            
            st.dataframe(
                df[available_cols].sort_index(ascending=False).head(100) # Latest 100 orders
                .style.map(lambda x: 'color: #ef5350' if isinstance(x, (int, float)) and x < 0 else 'color: #66bb6a', subset=['Net_Profit']),
                use_container_width=True
            )
            
        else:
            st.error(f"Columns missing! 'SKU Name' ya 'Bank Settlement [Projected] (INR)' nahi mila.")
            
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Aavoni: Please upload the Excel file containing the 'Orders P&L' sheet.")
