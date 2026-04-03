import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Business Dashboard", layout="wide", page_icon="📊")

st.title("📊 Aavoni Pro Business Dashboard")
st.markdown("Flipkart **Orders P&L** - Full Category Analysis (No Graphs).")

# --- SIDEBAR: COST SETTINGS ---
with st.sidebar:
    st.header("📊 Product Costing")
    std_base = st.number_input("Standard Pant Cost (PT/PL)", value=165)
    hf_base = st.number_input("HF Series Cost", value=110)
    st.divider()

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        excel_data = pd.ExcelFile(uploaded_file)
        target_sheet = next((s for s in excel_data.sheet_names if "Orders P&L" in s), excel_data.sheet_names[0])
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        
        # Cleanup column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Column Mappings
        sku_col = "SKU Name"
        units_col = "Net Units"
        settlement_col = "Bank Settlement [Projected] (INR)"
        status_col = "Order Status"
        gross_units_col = "Gross Units"
        
        if sku_col in df.columns and settlement_col in df.columns:
            # Data Cleaning
            df[units_col] = pd.to_numeric(df[units_col], errors='coerce').fillna(0).astype(int)
            df[settlement_col] = pd.to_numeric(df[settlement_col], errors='coerce').fillna(0)
            
            # Gross Units detection
            g_col = df.columns[df.columns.str.contains('Gross Units')][0]
            df[gross_units_col] = pd.to_numeric(df[g_col], errors='coerce').fillna(0).astype(int)

            # Categorization
            def get_cat_data(sku_name):
                sku = str(sku_name).upper()
                is_hf = sku.startswith("HF")
                if "3CBO" in sku: return "Std 3CBO", (std_base * 3)
                if "CBO" in sku:
                    return ("HF Combo", hf_base * 2) if is_hf else ("Std Combo", std_base * 2)
                return ("HF Single", hf_base) if is_hf else ("Std Single", std_base)

            results = df[sku_col].apply(get_cat_data)
            df['Category'] = [x[0] for x in results]
            df['Unit_Cost'] = [x[1] for x in results]
            
            # Profit Calculation
            df['Net_Profit'] = df.apply(
                lambda x: x[settlement_col] - (x[units_col] * x['Unit_Cost']) if x[units_col] > 0 else x[settlement_col], 
                axis=1
            )

            # --- 1. TOP LEVEL KPI METRICS ---
            t_pay = int(df[settlement_col].sum())
            t_prof = int(df['Net_Profit'].sum())
            t_gross = int(df[gross_units_col].sum())
            t_net_units = int(df[units_col].sum())
            
            return_rate = ((t_gross - t_net_units) / t_gross * 100) if t_gross > 0 else 0
            margin_pct = (t_prof / t_pay * 100) if t_pay > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Settlement", f"₹{t_pay:,}")
            m2.metric("Net Profit", f"₹{t_prof:,}", delta=f"{margin_pct:.1f}% Margin")
            m3.metric("Return Rate", f"{return_rate:.1f}%", delta_color="inverse", delta=f"{t_gross - t_net_units} Units Return")
            m4.metric("Net Units Sold", f"{t_net_units:,}")

            st.divider()

            # --- 2. CATEGORY PERFORMANCE TABLE (Detailed) ---
            st.subheader("💰 Category Performance: Sales vs Net Analysis")
            
            # Grouping 1: Total Category (Includes Returns)
            total_cat = df.groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            })

            # Grouping 2: Only Successful Sales (Units > 0)
            sales_only = df[df[units_col] > 0].groupby('Category').agg({
                units_col: 'sum',
                settlement_col: 'sum',
                'Net_Profit': 'sum'
            })

            # Building the Final Summary Table
            summary_table = pd.DataFrame(index=total_cat.index)
            summary_table['Net Units'] = total_cat[units_col]
            
            # Avg Sales (Bina return ke)
            summary_table['Avg Sales Sett.'] = (sales_only[settlement_col] / sales_only[units_col]).round(0)
            summary_table['Avg Sales Prof.'] = (sales_only['Net_Profit'] / sales_only[units_col]).round(0)
            
            # Net Avg (Return charges kaatne ke baad)
            summary_table['Net Avg Sett.'] = (total_cat[settlement_col] / total_cat[units_col]).round(0)
            summary_table['Net Avg Prof.'] = (total_cat['Net_Profit'] / total_cat[units_col]).round(0)

            # Display Table as Integers
            st.table(summary_table.fillna(0).astype(int))
            
            st.info("💡 **Avg Sales** = Jab order deliver hota hai | **Net Avg** = Returns ke charges minus hone ke baad asli recovery.")

            # --- 3. LOSS-MAKING SKU CHECK ---
            st.subheader("⚠️ Loss-making Orders (Negative Settlement/Profit)")
            loss_df = df[df['Net_Profit'] < 0][[sku_col, status_col, settlement_col, 'Net_Profit']].copy()
            if not loss_df.empty:
                st.dataframe(loss_df.sort_values('Net_Profit').astype(int, errors='ignore'), use_container_width=True, hide_index=True)
            else:
                st.success("Great! Koi bhi order negative profit mein nahi hai.")

            # --- 4. FULL ORDER LIST ---
            st.subheader("🔎 All Orders Breakdown")
            final_disp = df[[sku_col, 'Category', status_col, units_col, settlement_col, 'Net_Profit']].copy()
            final_disp[settlement_col] = final_disp[settlement_col].round(0).astype(int)
            final_disp['Net_Profit'] = final_disp['Net_Profit'].round(0).astype(int)
            
            st.dataframe(final_disp.sort_index(ascending=False), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Aavoni: Please upload the Orders P&L file.")
