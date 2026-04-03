import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Orders P&L Analyzer", layout="wide", page_icon="📦")

st.title("📦 Aavoni Order-level P&L Analyzer")
st.markdown("Flipkart **Orders P&L** Analysis (Sales Avg vs Net Avg with Returns).")

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
        target_sheet = next((s for s in excel_data.sheet_names if "Orders P&L" in s), excel_data.sheet_names[0])
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        df.columns = [str(c).strip() for c in df.columns]
        
        sku_col = "SKU Name"
        units_col = "Net Units"
        settlement_col = "Bank Settlement [Projected] (INR)"
        status_col = "Order Status"

        if sku_col in df.columns and settlement_col in df.columns:
            # Data Cleaning (Removing Decimals)
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0)

            # --- CATEGORIZATION ---
            def get_cat_and_cost(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                if "3CBO" in sku: return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            cat_results = df[sku_col].apply(get_cat_and_cost)
            df['Category'] = [x[0] for x in cat_results]
            df['Unit_Cost'] = [x[1] for x in cat_results]
            
            # Profit Calculation
            df['Net_Profit'] = df.apply(
                lambda x: x[settlement_col] - (x[units_col] * x['Unit_Cost']) if x[units_col] > 0 else x[settlement_col], 
                axis=1
            )

            # --- 1. SUMMARY METRICS ---
            t_pay = int(df[settlement_col].sum())
            t_prof = int(df['Net_Profit'].sum())
            t_units = int(df[units_col].sum())
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Net Settlement", f"₹{t_pay:,}")
            c2.metric("Total Net Profit", f"₹{t_prof:,}")
            c3.metric("Total Net Units", f"{t_units:,}")

            # --- 2. CATEGORY-WISE TABLE (Dono Averages ke saath) ---
            st.subheader("📊 Category Summary: Sales vs Net Analysis")
            
            # Grouping 1: Sirf Sales (Units > 0) - Pehle wala logic
            sales_only = df[df[units_col] > 0].groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            })
            
            # Grouping 2: Total Category (Sales + Returns) - Naya logic
            total_cat = df.groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            })

            # Calculation Table
            summary_table = pd.DataFrame(index=total_cat.index)
            summary_table['Net Units'] = total_cat[units_col]
            
            # A. Pehle wala Avg (Sales Only)
            summary_table['Avg Sales Sett.'] = (sales_only[settlement_col] / sales_only[units_col]).round(0)
            summary_table['Avg Sales Prof.'] = (sales_only['Net_Profit'] / sales_only[units_col]).round(0)
            
            # B. Naya Avg (Net with Returns)
            summary_table['Net Avg Sett.'] = (total_cat[settlement_col] / total_cat[units_col]).round(0)
            summary_table['Net Avg Prof.'] = (total_cat['Net_Profit'] / total_cat[units_col]).round(0)

            # Clean display
            st.table(summary_table.fillna(0).astype(int))
            
            st.info("""
            **Column Guide:**
            - **Avg Sales Sett./Prof:** Ye tab ka hai jab order deliver hota hai (Bina return ke nuksan ke).
            - **Net Avg Sett./Prof:** Isme returns ke negative charges kaatne ke baad jo asli bacha, wo hai.
            """)

            # --- 3. DETAILED DATA ---
            st.subheader("🔎 Detailed Order List")
            display_df = df[[sku_col, 'Category', units_col, settlement_col, 'Net_Profit']].copy()
            if status_col in df.columns:
                display_df.insert(2, status_col, df[status_col])

            display_df[settlement_col] = display_df[settlement_col].round(0).astype(int)
            display_df['Net_Profit'] = display_df['Net_Profit'].round(0).astype(int)

            st.dataframe(display_df.sort_index(ascending=False), use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Aavoni: Please upload the Orders P&L Excel file.")
