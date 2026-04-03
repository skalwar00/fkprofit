import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Orders P&L Analyzer", layout="wide", page_icon="📦")

st.title("📦 Aavoni Order-level P&L Analyzer")
st.markdown("Flipkart **Orders P&L** sheet ke base par calculation (No Decimals).")

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
        # Excel read karna aur Orders P&L sheet dhoondna
        excel_data = pd.ExcelFile(uploaded_file)
        target_sheet = next((s for s in excel_data.sheet_names if "Orders P&L" in s), excel_data.sheet_names[0])
        
        # Header selection (Flipkart sheets mein aksar top rows khali hoti hain)
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Required columns mapping
        sku_col = "SKU Name"
        units_col = "Net Units"
        settlement_col = "Bank Settlement [Projected] (INR)"
        status_col = "Order Status"

        if sku_col in df.columns and settlement_col in df.columns:
            # 1. Data Cleaning: Convert to Numeric and then to Integer (Removes Decimals)
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0).round(0).astype(int)

            # --- CATEGORIZATION LOGIC ---
            def get_cat_and_cost(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                if "3CBO" in sku: return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            # Apply categorization
            cat_results = df[sku_col].apply(get_cat_and_cost)
            df['Category'] = [x[0] for x in cat_results]
            df['Unit_Cost'] = [x[1] for x in cat_results]
            
            # Profit Calculation: Settlement - (Net Units * Cost)
            # Row level rounding to ensure no decimals in profit
            df['Net_Profit'] = df.apply(
                lambda x: x[settlement_col] - (x[units_col] * x['Unit_Cost']) if x[units_col] > 0 else x[settlement_col], 
                axis=1
            ).round(0).astype(int)

            # --- 1. SUMMARY METRICS ---
            t_pay = int(df[settlement_col].sum())
            t_prof = int(df['Net_Profit'].sum())
            t_units = int(df[units_col].sum())
            
            c1, c2, c3 = st.columns(3)
            # f-string formatting with {:,} adds commas but no decimals
            c1.metric("Total Settlement", f"₹{t_pay:,}")
            c2.metric("Net Profit (Cash)", f"₹{t_prof:,}")
            c3.metric("Total Net Units", f"{t_units:,}")

            # --- 2. CATEGORY-WISE TABLE ---
            st.subheader("📊 Category Summary")
            # Only summarize rows with active units to get better averages
            cat_summary = df[df[units_col] > 0].groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            }).rename(columns={units_col: 'Total Units'})
            
            # Category averages calculation (Rounded to 0 decimal)
            cat_summary['Avg Settlement'] = (cat_summary[settlement_col] / cat_summary['Total Units']).round(0).astype(int)
            cat_summary['Avg Profit'] = (cat_summary['Net_Profit'] / cat_summary['Total Units']).round(0).astype(int)
            
            # Ensure everything in table is Integer
            st.table(cat_summary[['Total Units', 'Avg Settlement', 'Avg Profit']].astype(int))

            # --- 3. FULL ORDER BREAKDOWN ---
            st.subheader("🔎 Order-wise Detailed Breakdown")
            
            # Displaying latest 100 rows for performance
            display_df = df[[sku_col, 'Category', units_col, settlement_col, 'Net_Profit']].copy()
            if status_col in df.columns:
                display_df.insert(2, status_col, df[status_col])

            st.dataframe(
                display_df.sort_index(ascending=False)
                .style.map(lambda x: 'color: #ef5350' if isinstance(x, (int, float)) and x < 0 else 'color: #66bb6a', subset=['Net_Profit']),
                use_container_width=True, hide_index=True
            )
            
        else:
            st.error(f"Columns mismatch! Check if 'SKU Name' and 'Bank Settlement [Projected] (INR)' exist in the sheet.")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Aavoni: Please upload the SKU/Order P&L Excel file.")
