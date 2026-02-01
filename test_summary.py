from financial_chatbot import query

# Get actual values for the three metrics
print('=== Projected Gross Profit (bf adj) ===')
# Projection sheet, Gross Profit trade
proj_gp = query(Sheet_Name='Projection', Trade='Gross Profit (Item 3.0-4.3)')
total = proj_gp['Value'].sum()
print(f'Total: {total:,.2f}')
print(proj_gp[['Item_Code', 'Trade', 'Value']].head(5).to_string())

print('\n=== WIP Gross Profit (bf adj) ===')
# Audit Report (WIP), Gross Profit trade
wip_gp = query(Sheet_Name='Financial Status', Financial_Type='Audit Report (WIP) J', Trade='Gross Profit (Item 3.0-4.3)')
total = wip_gp['Value'].sum()
print(f'Total: {total:,.2f}')
print(wip_gp[['Item_Code', 'Trade', 'Value']].head(5).to_string())

print('\n=== Cash Flow (Gross Profit related) ===')
# Cash Flow sheet
cf = query(Sheet_Name='Cash Flow', Trade='Gross Profit (Item 3.0-4.3)')
total = cf['Value'].sum()
print(f'Total: {total:,.2f}')
print(cf[['Item_Code', 'Trade', 'Value']].head(5).to_string())
