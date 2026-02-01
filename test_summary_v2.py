from financial_chatbot import initialize, get_financial_summary

initialize()

summary = get_financial_summary()
print('=== Financial Summary (December 2025) ===')
print(f'Projected Gross Profit (bf adj): ${summary["projected_gross_profit"]:,.2f}')
print(f'WIP Gross Profit (bf adj): ${summary["wip_gross_profit"]:,.2f}')
print(f'Cash Flow: ${summary["cash_flow"]:,.2f}')
