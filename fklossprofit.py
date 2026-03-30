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
        target_sheet = next((s for s in excel_data.sheet_names if "SKU-level" in s), excel_data.sheet_names[0])
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        df.columns = [str(c).strip() for c in df.columns]
        sku_col, units_col, settlement_col = "SKU ID", "Net Units (#)", "Bank Settlement [Projected] (INR)"

        if sku_col in df.columns and settlement_col in df.columns:
            # Data Cleaning
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0)

            # Categorization Function
            def get_cat_data(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                if "3CBO" in sku: return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            # Process Data
            rows = []
            for _, row in df.iterrows():
                cat, cost = get_cat_data(row[sku_col])
                u = row[units_col]
                pay = row[settlement_col]
                # Profit calculation (Net units based)
                prof = pay - (u * cost) if u > 0 else pay
                rows.append({'Category': cat, 'Units': u, 'Settlement': pay, 'Cost': cost, 'Profit': prof})

            res_df = pd.DataFrame(rows)

            # --- 1. AVERAGE CALCULATION TABLE ---
            st.subheader("📊 Category-wise Average Analysis")
            # Sirf positive sales wale units ka average nikalne ke liye
            avg_df = res_df[res_df['Units'] > 0].groupby('Category').agg({
                'Units': 'sum',
                'Settlement': 'sum',
                'Profit': 'sum'
            })
            
            # Avg Settlement = Total Settlement / Total Net Units
            avg_df['Avg Settlement'] = (avg_df['Settlement'] / avg_df['Units']).round(0).astype(int)
            # Avg Profit = Total Profit / Total Net Units
            avg_df['Avg Profit'] = (avg_df['Profit'] / avg_df['Units']).round(0).astype(int)
            
            # Displaying Table
            st.table(avg_df[['Units', 'Avg Settlement', 'Avg Profit']])

            # --- 2. SUMMARY METRICS ---
            st.divider()
            t_pay = df[settlement_col].sum()
            t_prof = res_df['Profit'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Settlement", f"₹{int(t_pay):,}")
            c2.metric("Net Profit (Cash)", f"₹{int(t_prof):,}")
            c3.metric("Total Net Units", f"{int(df[units_col].sum())}")

            # --- 3. FULL SKU BREAKDOWN ---
            st.subheader("🔎 SKU-wise Detailed Breakdown")
            df['Net_Profit'] = res_df['Profit'].round(0).astype(int)
            df_disp = df[[sku_col, units_col, settlement_col, 'Net_Profit']].copy()
            df_disp[settlement_col] = df_disp[settlement_col].round(0).astype(int)
            
            st.dataframe(
                df_disp.sort_values(by='Net_Profit', ascending=False)
                .style.applymap(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else 'color: green', subset=['Net_Profit']),
                use_container_width=True, hide_index=True
            )
            
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Aavoni: Please upload the SKU-level P&L file.")