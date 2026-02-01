# MEMORY.md - Long-term preferences

## Coding Tasks
- Use Claude Code CLI for all coding tasks (GLM-4.7 backend via z.ai)
- Run `claude --print "<task>"` for single-shot coding requests
- Run `claude` for interactive coding sessions

## Financial Chatbot Data Structure
- Data location: G:/My Drive/Ai Chatbot Knowledge Base
- Data structure: Year | Month | Sheet_Name | Financial_Type | Item_Code | Trade | Value
- Financial types: Tender A, 1st Working Budget B, Audit Report (WIP) J, Projection as at I, Cash Flow, etc.
- Trades: Gross Profit (Item 1.0-2.0) (Financial A/C), Gross Profit (Item 3.0-4.3), Income, Original Contract Works, etc.
- Sheets: Financial Status, Projection, Committed Cost, Accrual, Cash Flow

### Correct Query Functions (USE THESE):
```python
from financial_chatbot import initialize, get_projected_gross_profit, get_wip_gross_profit, get_cash_flow

initialize()
get_projected_gross_profit()  # Query: Projection sheet, Trade contains "Gross Profit"
get_wip_gross_profit()        # Query: Financial Status, Financial_Type="Audit Report (WIP) J", Trade contains "Gross Profit"
get_cash_flow()               # Query: Cash Flow sheet, Trade contains "Gross Profit"
```

### DO NOT USE OLD QUERY - IT RETURNS 0:
- OLD (returns 0): query(Trade='Gross Profit (bf adj)')
- NEW (works): get_projected_gross_profit(), get_wip_gross_profit(), get_cash_flow()

## Channels
- Telegram: Primary channel for Big Dee (6144027960)
