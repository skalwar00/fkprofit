import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="Aavoni Business Dashboard", layout="wide", page_icon="📊")

st.title("📊 Aavoni Pro Business Dashboard")
st.markdown("Flipkart **Orders P&L** - Loss Tracking with Order IDs.")

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
        order_id_col = "Order ID"
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
            g_cols = [c for c in df.columns if 'Gross Units' in c]
            df[gross_units_col] = pd.to_numeric(df[g_cols[0]], errors='coerce').fillna(0).astype(int) if g_cols else df[units_col]

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

            # --- 2. CATEGORY PERFORMANCE TABLE ---
            st.subheader("💰 Category Performance: Sales vs Net Analysis")
            total_cat = df.groupby('Category').agg({units_col: 'sum', settlement_col: 'sum', 'Net_Profit': 'sum'})
            sales_only = df[df[units_col] > 0].groupby('Category').agg({units_col: 'sum', settlement_col: 'sum', 'Net_Profit': 'sum'})

            summary_table = pd.DataFrame(index=total_cat.index)
            summary_table['Net Units'] = total_cat[units_col]
            summary_table['Avg Sales Sett.'] = (sales_only[settlement_col] / sales_only[units_col]).round(0)
            summary_table['Avg Sales Prof.'] = (sales_only['Net_Profit'] / sales_only[units_col]).round(0)
            summary_table['Net Avg Sett.'] = (total_cat[settlement_col] / total_cat[units_col]).round(0)
            summary_table['Net Avg Prof.'] = (total_cat['Net_Profit'] / total_cat[units_col]).round(0)

            st.table(summary_table.fillna(0).astype(int))

            # --- 3. LOSS-MAKING SKU CHECK (With Order ID) ---
            st.subheader("⚠️ Loss-making Orders (Details with Order ID)")
            # Selecting relevant columns including Order ID
            loss_cols = [order_id_col, sku_col, status_col, settlement_col, 'Net_Profit']
            # Only use columns that actually exist in the dataframe
            available_cols = [c for c in loss_cols if c in df.columns or c == 'Net_Profit']
            
            loss_df = df[df['Net_Profit'] < 0][available_cols].copy()
            
            if not loss_df.empty:
                # Formatting decimals to integers for clean look
                if settlement_col in loss_df.columns:
                    loss_df[settlement_col] = loss_df[settlement_col].round(0).astype(int)
                loss_df['Net_Profit'] = loss_df['Net_Profit'].round(0).astype(int)
                
                st.dataframe(loss_df.sort_values('Net_Profit'), use_container_width=True, hide_index=True)
            else:
                st.success("Great! Koi bhi order negative profit mein nahi hai.")

            # --- 4. FULL ORDER LIST ---
            st.subheader("🔎 All Orders Breakdown")
            final_disp = df[[order_id_col, sku_col, 'Category', status_col, units_col, settlement_col, 'Net_Profit']].copy()
            final_disp[settlement_col] = final_disp[settlement_col].round(0).astype(int)
            final_disp['Net_Profit'] = final_disp['Net_Profit'].round(0).astype(int)
            
            st.dataframe(final_disp.sort_index(ascending=False), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Aavoni: Please upload the Orders P&L file.")
