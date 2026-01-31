# CSV Formatting Criteria

## 1. Monthly Data Sheets (Projection, Committed Cost, Accrual, Cash Flow)

### Source Structure:
- Row 10: Sheet type header (e.g., "Projection", "Committed Cost")
- Row 11: Column headers (Item, Trade, Bal B/F, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Total)
- Row 12: Category header (e.g., "1", "Income") - **KEEP**
- Row 13+: Data items

### CSV Columns:
| Col | Header | Description |
|-----|--------|-------------|
| A | Item_Code | Item code (1, 1.1, 1.2.1, etc.) - includes category headers |
| B | Trade | Item name - preserve leading spaces for sub-items (e.g., "  -V.O. / C.E.") |
| C | Bal_BF | Balance brought forward |
| D | Apr | April value |
| E | May | May value |
| F | Jun | June value |
| G | Jul | July value |
| H | Aug | August value |
| I | Sep | September value |
| J | Oct | October value |
| K | Nov | November value |
| L | Dec | December value |
| M | Jan | January value Feb | February value |
| N | |
| O | Mar | March value |
| P | Total | Year total |

### Key Rules:
- ✅ Keep category headers (Item codes like "1", "2" with Trade names like "Income", "Cost")
- ✅ Preserve leading spaces in Trade names for sub-items
- ✅ Fill empty cells with 0
- ✅ Numeric values as floats (2 decimal places)

---

## 2. Financial Status Simplified

### Source Structure:
- A1:C9: Project info (company, code, name, dates)
- Row 11-14: Multi-row column headers
- Row 15+: Data items

### Output Files:
- `Financial_Status_ProjectInfo.json` - Project metadata
- `Financial_Status_Simple.csv` - Financial data

### ProjectInfo.json Structure:
```json
{
  "company": "Company Name",
  "project_code": "1234",
  "project_name": "Contract No. XXX - Project Description",
  "report_date": "YYYY-MM-DD",
  "start_date": "YYYY-MM-DD",
  "complete_date": "YYYY-MM-DD",
  "target_complete_date": "YYYY-MM-DD"
}
```

### Simple CSV Columns:
| Col | Header | Description |
|-----|--------|-------------|
| A | Item | Item code (1, 1.1, 2.3.1, etc.) |
| B | Trade | Item name |
| C | Budget_Revision | Latest budget (Revision as at) |
| D | Business_Plan | Business Plan value |
| E | Audit_Report_WIP | Audit Report (WIP) value |
| F | Projection | Projection value |

---

## 3. Parsing Rules Applied

| Rule | Implementation |
|------|----------------|
| Skip header rows (0-10) | `data_start_row = 12` for monthly, `data_start_row = 15` for Financial Status |
| Handle merged cells | pandas automatically reads as NaN, then `fillna(0)` |
| Preserve sub-item formatting | Don't strip whitespace from Trade column |
| Extract clean dates | Regex to find YYYY-MM-DD pattern |
| Numeric conversion | `pd.to_numeric(errors='coerce').fillna(0)` |
| Category headers | Keep simple integer Item_Code rows (1, 2, 3...) |

---

## 4. File Outputs Summary

| File | Format | Rows | Purpose |
|------|--------|------|---------|
| `Projection.csv` | CSV | 107 | Forecast data by month |
| `Committed_Cost.csv` | CSV | 107 | Contract values by month |
| `Accrual.csv` | CSV | 107 | Incurred amounts by month |
| `Cash_Flow.csv` | CSV | 107 | Cash movements by month |
| `Financial_Status_Simple.csv` | CSV | 30 | Key financial summary |
| `metadata.json` | JSON | - | Project metadata |
| `Financial_Status_ProjectInfo.json` | JSON | - | Financial Status project info |

---

## 5. Python Parser Files

| File | Purpose |
|------|---------|
| `excel_parser.py` | Parses monthly sheets (Projection, Committed Cost, Accrual, Cash Flow) |
| `financial_status_simple.py` | Parses simplified Financial Status |

---

## 6. Quick Reference: Column Mappings

### Monthly Sheets (0-indexed to A-P):
```
A=Item_Code, B=Trade, C=Bal_BF, D=Apr, E=May, F=Jun,
G=Jul, H=Aug, I=Sep, J=Oct, K=Nov, L=Dec,
M=Jan, N=Feb, O=Mar, P=Total
```

### Financial Status Simple:
```
A=Item, B=Trade, C=Budget_Revision, D=Business_Plan,
E=Audit_Report_WIP, F=Projection
```

### Project Info (A1:C9):
```
A1=Company, A2=Project Code, A3=Project Name,
A4=Report Date, A5=Start Date, A6=Complete Date,
A7=Target Complete Date
```

---

*Last Updated: 2026-01-31*
