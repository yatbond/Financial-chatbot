"""
Excel Chatbot - Streamlit Web App for Analyzing Construction Project Financial Data
"""

import streamlit as st
import pandas as pd
import pickle
from pathlib import Path
from financial_chatbot import initialize, get_projected_gross_profit, get_wip_gross_profit, get_cash_flow


# Page config
st.set_page_config(
    page_title="Excel Chatbot 📊",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def load_data():
    """Load the parsed Excel data."""
    data_path = Path(__file__).parent / "excel_data.pkl"
    if data_path.exists():
        with open(data_path, 'rb') as f:
            return pickle.load(f)
    return None


def get_financial_summary():
    """Get the three key financial metrics using correct query functions."""
    try:
        # Initialize the financial chatbot (uses G: drive data)
        initialize()
        
        return {
            'projected_gross_profit': get_projected_gross_profit(),
            'wip_gross_profit': get_wip_gross_profit(),
            'cash_flow': get_cash_flow()
        }
    except Exception as e:
        st.error(f"Error loading financial data: {e}")
        return {'projected_gross_profit': 0, 'wip_gross_profit': 0, 'cash_flow': 0}


def get_answer(data: dict, question: str, selected_sheet: str) -> str:
    """
    Generate an answer to a question about the Excel data.
    Uses simple keyword matching and data queries.
    """
    df = data['sheets'].get(selected_sheet, pd.DataFrame())
    
    if df.empty:
        return "No data available for the selected sheet."
    
    question = question.lower()
    
    # Get column names for matching
    columns = [c.lower() for c in df.columns]
    
    # Total of numeric columns
    numeric_cols = [c for c in df.columns if c not in ['Item_Code', 'Item_Name']]
    
    # Common patterns
    if 'total' in question or 'sum' in question or 'how much' in question:
        # Find which column they're asking about
        for col in numeric_cols:
            if col.lower() in question:
                total = df[col].sum()
                return f"Total {col.replace('_', ' ')}: {total:,.2f}"
        # Default to total of all numeric columns
        totals = {col: df[col].sum() for col in numeric_cols}
        return "Totals:\n" + "\n".join([f"- {k}: {v:,.2f}" for k, v in totals.items()])
    
    elif 'average' in question or 'avg' in question:
        for col in numeric_cols:
            if col.lower() in question:
                avg = df[col].mean()
                return f"Average {col.replace('_', ' ')}: {avg:,.2f}"
    
    elif 'max' in question or 'highest' in question:
        for col in numeric_cols:
            if col.lower() in question:
                max_val = df[col].max()
                max_row = df[df[col] == max_val]['Item_Name'].values
                if len(max_row) > 0:
                    return f"Highest {col.replace('_', ' ')}: {max_val:,.2f} ({max_row[0]})"
    
    elif 'min' in question or 'lowest' in question:
        for col in numeric_cols:
            if col.lower() in question:
                min_val = df[col].min()
                min_row = df[df[col] == min_val]['Item_Name'].values
                if len(min_row) > 0:
                    return f"Lowest {col.replace('_', ' ')}: {min_val:,.2f} ({min_row[0]})"
    
    elif 'count' in question or 'how many' in question:
        non_zero = (df[numeric_cols] > 0).sum().sum()
        return f"Total non-zero values across all numeric columns: {non_zero}"
    
    elif 'item' in question or 'code' in question:
        # Show item breakdown
        return f"There are {len(df)} line items in {selected_sheet}. First 10:\n" + \
               df[['Item_Code', 'Item_Name']].head(10).to_string(index=False)
    
    elif 'row' in question or 'line' in question:
        return f"There are {len(df)} data rows (line items) in {selected_sheet}."
    
    elif 'budget' in question:
        if 'budget' in columns:
            total = df['Budget_1st'].sum()
            return f"Total Budget (1st Working): {total:,.2f}"
    
    elif 'committed' in question:
        if 'committed_value' in columns:
            total = df['Committed_Value'].sum()
            return f"Total Committed Value: {total:,.2f}"
    
    elif 'accrual' in question:
        if 'accrual' in columns:
            total = df['Accrual'].sum()
            return f"Total Accrual: {total:,.2f}"
    
    elif 'cash' in question:
        if 'cash_flow' in columns:
            total = df['Cash_Flow'].sum()
            return f"Total Cash Flow: {total:,.2f}"
    
    elif 'balance' in question:
        if 'balance' in columns:
            total = df['Balance'].sum()
            return f"Total Balance: {total:,.2f}"
    
    elif 'projection' in question:
        if 'projection' in columns:
            total = df['Projection'].sum()
            return f"Total Projection: {total:,.2f}"
    
    else:
        # Generic search in Item_Name
        matches = df[df['Item_Name'].str.lower().str.contains(question, na=False)]
        if len(matches) > 0:
            return f"Found {len(matches)} items matching '{question}':\n\n" + \
                   matches[['Item_Code', 'Item_Name'] + numeric_cols[:3]].head(10).to_string(index=False)
    
    return f"I couldn't understand the question about '{question}'. Try asking about:\n" \
           f"- Total [column name]\n" \
           f"- Average [column name]\n" \
           f"- Highest [column name]\n" \
           f"- Item codes\n" \
           f"- Budget/Committed/Accrual/Cash Flow/Balance totals"


def main():
    # Title
    st.title("📊 Financial Chatbot")
    st.caption("Construction Project Financial Data Analysis")
    
    # Initialize financial chatbot (loads from G: drive)
    try:
        initialize()
    except Exception as e:
        st.error(f"Error initializing: {e}")
        return
    
    # Get financial summary using correct query functions
    summary = get_financial_summary()
    
    # Display key metrics at the top
    st.markdown("### 📈 Financial Summary (December 2025)")
    cols = st.columns(3)
    cols[0].metric("Projected Gross Profit (bf adj)", f"${summary['projected_gross_profit']:,.2f}")
    cols[1].metric("WIP Gross Profit (bf adj)", f"${summary['wip_gross_profit']:,.2f}")
    cols[2].metric("Cash Flow", f"${summary['cash_flow']:,.2f}")
    
    # Show data from financial_chatbot
    st.markdown("---")
    st.subheader("💬 Ask about your data")
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your financial data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response using financial_chatbot query
        with st.chat_message("assistant"):
            from financial_chatbot import query
            response = answer_question(prompt)
            st.markdown(response)
        
        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


def answer_question(question):
    """Answer questions using financial_chatbot query functions."""
    question = question.lower()
    
    # Check for specific financial metrics
    if 'projected gross profit' in question:
        val = get_projected_gross_profit()
        return f"Projected Gross Profit (before adjustment): ${val:,.2f}"
    
    if 'wip gross profit' in question or 'wip gp' in question:
        val = get_wip_gross_profit()
        return f"WIP Gross Profit (before adjustment): ${val:,.2f}"
    
    if 'cash flow' in question:
        val = get_cash_flow()
        return f"Cash Flow: ${val:,.2f}"
    
    if 'total' in question or 'sum' in question:
        # Generic total query
        result = query()
        if not result.empty:
            total = result['Value'].sum()
            return f"Total value across all data: ${total:,.2f}"
    
    if 'how many' in question or 'count' in question:
        result = query()
        if not result.empty:
            return f"Total data points: {len(result)}"
    
    if 'projection' in question:
        result = query(Sheet_Name='Projection')
        if not result.empty:
            return f"Projection data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'audit report' in question or 'wip' in question:
        result = query(Sheet_Name='Financial Status', Financial_Type='Audit Report (WIP) J')
        if not result.empty:
            return f"Audit Report (WIP) data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'financial status' in question:
        result = query(Sheet_Name='Financial Status')
        if not result.empty:
            return f"Financial Status data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'cash flow' in question:
        result = query(Sheet_Name='Cash Flow')
        if not result.empty:
            return f"Cash Flow data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'accrual' in question:
        result = query(Sheet_Name='Accrual')
        if not result.empty:
            return f"Accrual data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'committed cost' in question:
        result = query(Sheet_Name='Committed Cost')
        if not result.empty:
            return f"Committed Cost data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'budget' in question:
        result = query(Financial_Type='1st Working Budget B')
        if not result.empty:
            return f"1st Working Budget data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'tender' in question:
        result = query(Financial_Type='Tender A')
        if not result.empty:
            return f"Tender A data: {len(result)} records\nTotal value: ${result['Value'].sum():,.2f}"
    
    if 'gross profit' in question:
        result = query()
        if not result.empty:
            # Filter for Gross Profit trades
            gp = result[result['Trade'].str.contains('Gross Profit', case=False, na=False)]
            if not gp.empty:
                return f"Gross Profit data: {len(gp)} records\nTotal value: ${gp['Value'].sum():,.2f}"
    
    if 'item' in question:
        result = query()
        if not result.empty:
            items = result['Item_Code'].unique()
            return f"Available Item Codes: {len(items)} items\nExamples: {', '.join(items[:10])}"
    
    return f"I found {len(query())} total records in the financial database. Try asking about:\n" \
           f"- Projected Gross Profit\n" \
           f"- WIP Gross Profit\n" \
           f"- Cash Flow\n" \
           f"- Budget/Projection/Audit Report totals\n" \
           f"- Specific sheets (Financial Status, Projection, Cash Flow, etc.)"


if __name__ == "__main__":
    main()
