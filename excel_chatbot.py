"""
Excel Chatbot - Streamlit Web App for Analyzing Construction Project Financial Data
"""

import streamlit as st
import pandas as pd
import traceback

# Page config
st.set_page_config(
    page_title="Excel Chatbot 📊",
    page_icon="📊",
    layout="wide"
)

# Initialize at module level with error handling
_data_cache = None

def initialize_data():
    """Initialize the financial data."""
    global _data_cache
    
    try:
        from financial_preprocessor import load_all_data, DEFAULT_DATA_ROOT
        
        # Check if data folder exists
        import os
        if not os.path.exists(DEFAULT_DATA_ROOT):
            return None, f"Data folder not found: {DEFAULT_DATA_ROOT}"
        
        _data_cache = load_all_data(DEFAULT_DATA_ROOT)
        return _data_cache, "Success"
        
    except Exception as e:
        return None, f"Error: {str(e)}\n{traceback.format_exc()}"

def query(**filters):
    """Query the financial data."""
    global _data_cache
    if _data_cache is None or _data_cache.empty:
        df, status = initialize_data()
        if df is None:
            return pd.DataFrame()
        _data_cache = df
    
    result = _data_cache.copy()
    for key, value in filters.items():
        if key not in result.columns:
            continue
        if isinstance(value, list):
            result = result[result[key].isin(value)]
        else:
            result = result[result[key] == value]
    return result

def main():
    st.title("📊 Financial Chatbot")
    st.caption("Construction Project Financial Data Analysis")
    
    # Initialize data
    df, status = initialize_data()
    
    if df is None:
        st.warning(status)
        st.info("Please configure the data source.")
        return
    
    if df.empty:
        st.warning("No data loaded. Please add Excel files to the data folder.")
        return
    
    st.success(f"Loaded {len(df)} records from {df['_source_file'].nunique()} files")
    
    # Show data summary
    st.markdown("### 📈 Data Summary")
    st.write(f"Available sheets: {df['Sheet_Name'].unique().tolist()}")
    st.write(f"Available years: {df['Year'].unique().tolist()}")
    st.write(f"Available months: {df['Month'].unique().tolist()}")
    
    # Show sample data
    with st.expander("Sample Data", expanded=False):
        st.dataframe(df.head(10))

if __name__ == "__main__":
    main()
