"""
Excel Chatbot - Streamlit Web App for Analyzing Construction Project Financial Data
"""

import streamlit as st
import pandas as pd
import pickle
from pathlib import Path


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
    st.title("📊 Excel Chatbot")
    st.caption("Ask questions about your construction project financial data")
    
    # Load data
    data = load_data()
    
    if data is None:
        st.error("No data found. Please run excel_parser.py first.")
        return
    
    # Show metadata
    with st.expander("📋 Project Information", expanded=False):
        metadata = data.get('metadata', {})
        for key, value in metadata.items():
            st.text(f"{key.replace('_', ' ').title()}: {value}")
    
    # Sidebar - Sheet selection
    st.sidebar.title("📁 Sheet Selection")
    sheets = list(data['sheets'].keys())
    selected_sheet = st.sidebar.selectbox("Choose a sheet:", sheets)
    
    # Show sheet info
    df = data['sheets'][selected_sheet]
    st.sidebar.text(f"Rows: {len(df)}")
    st.sidebar.text(f"Columns: {len(df.columns)}")
    
    # Show column names
    st.sidebar.markdown("### Columns")
    for col in df.columns:
        st.sidebar.text(f"- {col}")
    
    # Main content - Data preview
    with st.expander("📊 Data Preview", expanded=False):
        st.dataframe(df, use_container_width=True)
    
    # Chat interface
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
    if prompt := st.chat_input("Ask a question about your data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            response = get_answer(data, prompt, selected_sheet)
            st.markdown(response)
        
        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Quick questions
    st.markdown("### � Quick Questions")
    cols = st.columns(3)
    questions = [
        ("Total Budget", "What is the total budget?"),
        ("Total Committed", "What is the total committed value?"),
        ("All Totals", "Show all column totals"),
    ]
    for i, (label, question) in enumerate(questions):
        if cols[i].button(label):
            response = get_answer(data, question, selected_sheet)
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()


if __name__ == "__main__":
    main()
