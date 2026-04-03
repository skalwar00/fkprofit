import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Profit Dashboard", layout="wide", page_icon="📈")

st.title("📈 Aavoni Average Profit & Settlement Analyzer")
st.markdown("Flipkart **SKU-level P&L** Excel upload karein.")

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
        # Auto-detect sheet with "SKU-level" or take the first one
        target_sheet = next((s for s in excel_data.sheet_names if "SKU-level" in s), excel_data.sheet_names[0])
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Define required columns (matching your Flipkart export)
        sku_col = "SKU ID"
        units_col = "Net Units (#)"
        settlement_col = "Bank Settlement [Projected] (INR)"

        if sku_col in df.columns and settlement_col in df.columns:
            # Data Cleaning
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0)

            # --- CATEGORIZATION LOGIC ---
            def get_cat_and_cost(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                
                if "3CBO" in sku:
                    return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            # Apply logic efficiently
            cat_results = df[sku_col].apply(get_cat_and_cost)
            df['Category'] = [x[0] for x in cat_results]
            df['Unit_Cost'] = [x[1] for x in cat_results]
            
            # Profit Calculation: Settlement - (Net Units * Cost)
            # If Net Units is 0 or negative (returns), we treat the settlement as is.
            df['Net_Profit'] = df.apply(
                lambda x: x[settlement_col] - (x[units_col] * x['Unit_Cost']) if x[units_col] > 0 else x[settlement_col], 
                axis=1
            )

            # --- 1. AVERAGE CALCULATION TABLE ---
            st.subheader("📊 Category-wise Average Analysis")
            
            # Filter for rows where sales actually happened to avoid skewing averages
            active_sales = df[df[units_col] > 0]
            
            if not active_sales.empty:
                avg_df = active_sales.groupby('Category').agg({
                    units_col: 'sum',
                    settlement_col: 'sum',
                    'Net_Profit': 'sum'
                }).rename(columns={units_col: 'Total Units'})
                
                avg_df['Avg Settlement'] = (avg_df[settlement_col] / avg_df['Total Units']).round(0).astype(int)
                avg_df['Avg Profit'] = (avg_df['Net_Profit'] / avg_df['Total Units']).round(0).astype(int)
                
                st.table(avg_df[['Total Units', 'Avg Settlement', 'Avg Profit']])
            else:
                st.warning("No positive net units found to calculate averages.")

            # --- 2. SUMMARY METRICS ---
            st.divider()
            t_pay = df[settlement_col].sum()
            t_prof = df['Net_Profit'].sum()
            t_units = df[units_col].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Settlement", f"₹{int(t_pay):,}")
            c2.metric("Net Profit (Cash)", f"₹{int(t_prof):,}", delta=f"{((t_prof/t_pay)*100):.1f}% Margin" if t_pay != 0 else None)
            c3.metric("Total Net Units", f"{int(t_units)}")

            # --- 3. FULL SKU BREAKDOWN ---
            st.subheader("🔎 SKU-wise Detailed Breakdown")
            df_disp = df[[sku_col, 'Category', units_col, settlement_col, 'Net_Profit']].copy()
            
            # Formatting for display
            df_disp[settlement_col] = df_disp[settlement_col].round(0).astype(int)
            df_disp['Net_Profit'] = df_disp['Net_Profit'].round(0).astype(int)
            
            st.dataframe(
                df_disp.sort_values(by='Net_Profit', ascending=False)
                .style.map(lambda x: 'color: #ef5350' if isinstance(x, (int, float)) and x < 0 else 'color: #66bb6a', subset=['Net_Profit']),
                use_container_width=True, hide_index=True
            )
            
        else:
            st.error(f"Required columns not found! Need: {sku_col} and {settlement_col}")
            
    except Exception as e:
        st.error(f"Technical Locha: {e}")
else:
    st.info("Aavoni: Please upload the SKU-level P&L file to start the analysis.")
