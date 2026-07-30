import streamlit as st
import pandas as pd
import os
from modules.calculator import Calculator
from modules.currency import CurrencyConverter
st.set_page_config(layout='wide')
calc, curr = Calculator(), CurrencyConverter()
st.title('🥛 Dairy Yield & Cost Dashboard')
target_curr = st.selectbox('Currency', list(curr.exchange_rates.keys()), index=1)
sym = curr.get_currency_symbol(target_curr)
col1, col2 = st.columns(2)
input_item = col1.selectbox('Product', calc.get_supported_products())
qty = col2.number_input('Quantity', value=100.0)
if st.button('Calculate'):
    y, c = calc.calculate_yield(input_item, qty), calc.calculate_costs(input_item, qty, calc.calculate_yield(input_item, qty))
    k1, k2, k3 = st.columns(3)
    k1.metric('Input Cost', f'{sym}{curr.convert_from_base(c["total_input_cost"], target_curr):,.2f}')
    k2.metric('Yield Value', f'{sym}{curr.convert_from_base(c["total_output_value"], target_curr):,.2f}')
    k3.metric('Net', f'{sym}{curr.convert_from_base(c["profit_loss"], target_curr):,.2f}')
    st.table(pd.DataFrame([{'Product': p, 'Yield': f'{d["quantity"]:.2f} {d["unit"]}'} for p, d in y.items()]))