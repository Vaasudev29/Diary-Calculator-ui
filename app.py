import csv
import io
import os
from collections import Counter
from datetime import datetime

import streamlit as st

from calculator import Calculator
from business_opportunity.ui import render_business_opportunity
from currency import CurrencyConverter
from dairy_analysis.ui import render_dairy_industry_analysis
from market_opportunities.ui import render_market_opportunities
from price_intelligence.ui import render_prices
from process_calculators import (
    calculate_butter,
    calculate_cheese_yield,
    calculate_ghee,
    calculate_paneer_yield,
    calculate_production_cost,
    calculate_profit,
    standardize_milk,
)

st.set_page_config(
    page_title="Dairy Process Calculator Suite",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_styles():
    styles_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(styles_path, encoding="utf-8") as styles_file:
        st.markdown(f"<style>{styles_file.read()}</style>", unsafe_allow_html=True)


def render_table(rows):
    table_rows = "\n".join(f"| {label} | {value} |" for label, value in rows)
    st.markdown(f"| Measure | Result |\n| --- | ---: |\n{table_rows}")


def record_calculation(module, summary, value):
    history = st.session_state.setdefault("calculation_history", [])
    history.append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "module": module,
            "summary": summary,
            "value": value,
        }
    )
    del history[:-25]


def render_dairy_yield_calculator(calculator, currency_converter):
    st.title("Dairy Yield Calculator")
    st.caption("Existing V1 calculator - yield and cost logic preserved.")

    with st.container(border=True):
        st.subheader("Process inputs")
        input_column, quantity_column, currency_column = st.columns(3)
        input_item = input_column.selectbox(
            "Input product",
            calculator.get_supported_products(),
            help="Select the dairy product to process.",
        )
        quantity = quantity_column.number_input(
            "Input quantity",
            min_value=0.0,
            value=100.0,
            step=1.0,
            help="Quantity is interpreted in the selected product's source unit.",
        )
        target_currency = currency_column.selectbox(
            "Display currency",
            list(currency_converter.exchange_rates.keys()),
            index=1,
        )
        calculate = st.button("Calculate yield and value", type="primary", use_container_width=True)

    if not calculate:
        st.info("Enter a product and quantity, then calculate to view process yields and costs.")
        return

    # These calls intentionally use the original V1 Calculator business logic.
    yields = calculator.calculate_yield(input_item, quantity)
    costs = calculator.calculate_costs(input_item, quantity, yields)
    symbol = currency_converter.get_currency_symbol(target_currency)

    st.subheader("Process summary")
    input_cost, yield_value, net_value = st.columns(3)
    input_cost.metric(
        "Input cost",
        f"{symbol}{currency_converter.convert_from_base(costs['total_input_cost'], target_currency):,.2f}",
    )
    yield_value.metric(
        "Yield value",
        f"{symbol}{currency_converter.convert_from_base(costs['total_output_value'], target_currency):,.2f}",
    )
    net_value.metric(
        "Net value",
        f"{symbol}{currency_converter.convert_from_base(costs['profit_loss'], target_currency):,.2f}",
        delta=f"{symbol}{currency_converter.convert_from_base(costs['profit_loss'], target_currency):,.2f}",
    )

    st.subheader("Yield breakdown")
    render_table(
        [(product, f"{details['quantity']:.2f} {details['unit']}") for product, details in yields.items()]
    )
    record_calculation("Dairy Yield", f"{input_item}: {quantity:.2f}", costs["profit_loss"])


def render_milk_standardization():
    st.title("Milk Standardization")
    st.caption("Balance milk fat by adding cream or skim milk.")
    with st.form("milk_standardization"):
        milk_quantity, source_fat, target_fat = st.columns(3)
        milk_quantity = milk_quantity.number_input("Milk quantity (kg)", min_value=0.01, value=100.0)
        source_fat = source_fat.number_input("Source fat (%)", min_value=0.01, max_value=20.0, value=4.5)
        target_fat = target_fat.number_input("Target fat (%)", min_value=0.01, max_value=20.0, value=3.5)
        skim_fat, cream_fat = st.columns(2)
        skim_fat = skim_fat.number_input("Skim milk fat (%)", min_value=0.0, max_value=3.0, value=0.05)
        cream_fat = cream_fat.number_input("Cream fat (%)", min_value=20.0, max_value=80.0, value=40.0)
        calculate = st.form_submit_button("Standardize milk", type="primary")

    if not calculate:
        return
    if target_fat >= cream_fat or target_fat <= skim_fat:
        st.error("Target fat must be between the skim milk and cream fat percentages.")
        return

    result = standardize_milk(milk_quantity, source_fat, target_fat, skim_fat, cream_fat)
    st.subheader(result["method"])
    output, adjustment, fat = st.columns(3)
    output.metric("Standardized milk", f"{result['standardized_milk']:.2f} kg")
    adjustment.metric(
        "Adjustment",
        f"{result['cream_added'] + result['skim_added']:.2f} kg",
    )
    fat.metric("Target fat", f"{result['target_fat_pct']:.2f}%")
    render_table(
        [
            ("Cream added", f"{result['cream_added']:.2f} kg"),
            ("Skim milk added", f"{result['skim_added']:.2f} kg"),
        ]
    )
    record_calculation("Milk Standardization", result["method"], result["standardized_milk"])


def render_paneer_yield():
    st.title("Paneer Yield")
    st.caption("Estimate yield from recovered milk solids and final paneer moisture.")
    with st.form("paneer_yield"):
        milk_quantity, fat, snf = st.columns(3)
        milk_quantity = milk_quantity.number_input("Milk quantity (kg)", min_value=0.01, value=100.0)
        fat = fat.number_input("Milk fat (%)", min_value=0.01, max_value=20.0, value=4.5)
        snf = snf.number_input("Milk SNF (%)", min_value=0.01, max_value=20.0, value=8.5)
        fat_recovery, snf_recovery, moisture = st.columns(3)
        fat_recovery = fat_recovery.number_input("Fat recovery (%)", min_value=0.01, max_value=100.0, value=95.0)
        snf_recovery = snf_recovery.number_input("SNF recovery (%)", min_value=0.01, max_value=100.0, value=55.0)
        moisture = moisture.number_input("Paneer moisture (%)", min_value=0.01, max_value=90.0, value=55.0)
        calculate = st.form_submit_button("Calculate paneer yield", type="primary")

    if not calculate:
        return
    result = calculate_paneer_yield(milk_quantity, fat, snf, fat_recovery, snf_recovery, moisture)
    yield_column, solids_column, whey_column = st.columns(3)
    yield_column.metric("Paneer yield", f"{result['paneer_yield']:.2f} kg")
    solids_column.metric("Yield percentage", f"{result['yield_pct']:.2f}%")
    whey_column.metric("Whey estimate", f"{result['whey']:.2f} kg")
    render_table([("Retained solids", f"{result['retained_solids']:.2f} kg"), ("Target moisture", f"{moisture:.2f}%")])
    record_calculation("Paneer Yield", f"{result['yield_pct']:.2f}% yield", result["paneer_yield"])


def render_butter_calculator():
    st.title("Butter Calculator")
    st.caption("Estimate butter output from recovered cream fat.")
    with st.form("butter_calculator"):
        cream_quantity, cream_fat, butter_fat, recovery = st.columns(4)
        cream_quantity = cream_quantity.number_input("Cream quantity (kg)", min_value=0.01, value=100.0)
        cream_fat = cream_fat.number_input("Cream fat (%)", min_value=0.01, max_value=100.0, value=40.0)
        butter_fat = butter_fat.number_input("Butter fat (%)", min_value=0.01, max_value=100.0, value=82.0)
        recovery = recovery.number_input("Fat recovery (%)", min_value=0.01, max_value=100.0, value=98.0)
        calculate = st.form_submit_button("Calculate butter yield", type="primary")

    if not calculate:
        return
    result = calculate_butter(cream_quantity, cream_fat, butter_fat, recovery)
    butter, buttermilk, recovery_metric = st.columns(3)
    butter.metric("Butter yield", f"{result['butter_yield']:.2f} kg")
    buttermilk.metric("Buttermilk estimate", f"{result['buttermilk']:.2f} kg")
    recovery_metric.metric("Cream-to-butter yield", f"{result['yield_pct']:.2f}%")
    render_table([("Recovered fat", f"{result['recovered_fat']:.2f} kg"), ("Butter fat target", f"{butter_fat:.2f}%")])
    record_calculation("Butter Calculator", f"{result['butter_yield']:.2f} kg butter", result["butter_yield"])


def render_ghee_calculator():
    st.title("Ghee Calculator")
    st.caption("Estimate ghee output from recovered butterfat at the selected purity.")
    with st.form("ghee_calculator"):
        butter_quantity, butter_fat, purity, recovery = st.columns(4)
        butter_quantity = butter_quantity.number_input("Butter quantity (kg)", min_value=0.01, value=100.0)
        butter_fat = butter_fat.number_input("Butter fat (%)", min_value=0.01, max_value=100.0, value=82.0)
        purity = purity.number_input("Ghee purity (%)", min_value=0.01, max_value=100.0, value=99.5)
        recovery = recovery.number_input("Fat recovery (%)", min_value=0.01, max_value=100.0, value=99.0)
        calculate = st.form_submit_button("Calculate ghee yield", type="primary")

    if not calculate:
        return
    result = calculate_ghee(butter_quantity, butter_fat, purity, recovery)
    ghee, residue, yield_metric = st.columns(3)
    ghee.metric("Ghee yield", f"{result['ghee_yield']:.2f} kg")
    residue.metric("Residue estimate", f"{result['residue']:.2f} kg")
    yield_metric.metric("Butter-to-ghee yield", f"{result['yield_pct']:.2f}%")
    render_table([("Recovered fat", f"{result['recovered_fat']:.2f} kg"), ("Ghee purity", f"{purity:.2f}%")])
    record_calculation("Ghee Calculator", f"{result['ghee_yield']:.2f} kg ghee", result["ghee_yield"])


def render_cheese_calculator():
    st.title("Cheese Calculator")
    st.caption("Estimate cheese yield from retained fat, SNF, and final cheese moisture.")
    with st.form("cheese_calculator"):
        milk_quantity, fat, snf = st.columns(3)
        milk_quantity = milk_quantity.number_input("Milk quantity (kg)", min_value=0.01, value=100.0)
        fat = fat.number_input("Milk fat (%)", min_value=0.01, max_value=20.0, value=3.5)
        snf = snf.number_input("Milk SNF (%)", min_value=0.01, max_value=20.0, value=8.5)
        fat_recovery, snf_recovery, moisture = st.columns(3)
        fat_recovery = fat_recovery.number_input("Fat recovery (%)", min_value=0.01, max_value=100.0, value=93.0)
        snf_recovery = snf_recovery.number_input("SNF recovery (%)", min_value=0.01, max_value=100.0, value=50.0)
        moisture = moisture.number_input("Cheese moisture (%)", min_value=0.01, max_value=90.0, value=40.0)
        calculate = st.form_submit_button("Calculate cheese yield", type="primary")

    if not calculate:
        return
    result = calculate_cheese_yield(milk_quantity, fat, snf, fat_recovery, snf_recovery, moisture)
    yield_column, solids_column, whey_column = st.columns(3)
    yield_column.metric("Cheese yield", f"{result['cheese_yield']:.2f} kg")
    solids_column.metric("Yield percentage", f"{result['yield_pct']:.2f}%")
    whey_column.metric("Whey estimate", f"{result['whey']:.2f} kg")
    render_table([("Retained solids", f"{result['retained_solids']:.2f} kg"), ("Target moisture", f"{moisture:.2f}%")])
    record_calculation("Cheese Calculator", f"{result['yield_pct']:.2f}% yield", result["cheese_yield"])


def render_production_cost(currency_converter):
    st.title("Production Cost")
    st.caption("Build a cost per output unit from material, processing, and overhead inputs.")
    with st.form("production_cost"):
        input_quantity, input_cost, output_quantity = st.columns(3)
        input_quantity = input_quantity.number_input("Input quantity", min_value=0.01, value=100.0)
        input_cost = input_cost.number_input("Input cost per unit (INR)", min_value=0.0, value=40.0)
        output_quantity = output_quantity.number_input("Output quantity", min_value=0.01, value=18.0)
        labor, utilities, packaging, overhead = st.columns(4)
        labor = labor.number_input("Labor cost (INR)", min_value=0.0, value=500.0)
        utilities = utilities.number_input("Utilities cost (INR)", min_value=0.0, value=300.0)
        packaging = packaging.number_input("Packaging cost (INR)", min_value=0.0, value=250.0)
        overhead = overhead.number_input("Overhead (%)", min_value=0.0, max_value=100.0, value=10.0)
        target_currency = st.selectbox("Display currency", list(currency_converter.exchange_rates.keys()), index=0)
        calculate = st.form_submit_button("Calculate production cost", type="primary")

    if not calculate:
        return
    result = calculate_production_cost(input_quantity, input_cost, labor, utilities, packaging, overhead, output_quantity)
    symbol = currency_converter.get_currency_symbol(target_currency)
    total_cost, unit_cost, material_cost = st.columns(3)
    total_cost.metric("Total production cost", f"{symbol}{currency_converter.convert_from_base(result['total_cost'], target_currency):,.2f}")
    unit_cost.metric("Cost per output unit", f"{symbol}{currency_converter.convert_from_base(result['cost_per_output_unit'], target_currency):,.2f}")
    material_cost.metric("Material cost", f"{symbol}{currency_converter.convert_from_base(result['material_cost'], target_currency):,.2f}")
    render_table(
        [
            ("Labor", f"{symbol}{currency_converter.convert_from_base(result['labor_cost'], target_currency):,.2f}"),
            ("Utilities", f"{symbol}{currency_converter.convert_from_base(result['utilities_cost'], target_currency):,.2f}"),
            ("Packaging", f"{symbol}{currency_converter.convert_from_base(result['packaging_cost'], target_currency):,.2f}"),
            ("Overhead", f"{symbol}{currency_converter.convert_from_base(result['overhead_cost'], target_currency):,.2f}"),
        ]
    )
    record_calculation("Production Cost", f"{output_quantity:.2f} output units", result["total_cost"])


def render_profit_analysis(currency_converter):
    st.title("Profit Analysis")
    st.caption("Calculate contribution, profit, margin, and break-even quantity.")
    with st.form("profit_analysis"):
        sales_quantity, selling_price, variable_cost, fixed_cost = st.columns(4)
        sales_quantity = sales_quantity.number_input("Sales quantity", min_value=0.01, value=100.0)
        selling_price = selling_price.number_input("Selling price per unit (INR)", min_value=0.0, value=350.0)
        variable_cost = variable_cost.number_input("Variable cost per unit (INR)", min_value=0.0, value=250.0)
        fixed_cost = fixed_cost.number_input("Fixed cost (INR)", min_value=0.0, value=5000.0)
        target_currency = st.selectbox("Display currency", list(currency_converter.exchange_rates.keys()), index=0)
        calculate = st.form_submit_button("Calculate profit", type="primary")

    if not calculate:
        return
    result = calculate_profit(sales_quantity, selling_price, variable_cost, fixed_cost)
    symbol = currency_converter.get_currency_symbol(target_currency)
    revenue, profit, margin = st.columns(3)
    revenue.metric("Revenue", f"{symbol}{currency_converter.convert_from_base(result['revenue'], target_currency):,.2f}")
    profit.metric("Profit", f"{symbol}{currency_converter.convert_from_base(result['profit'], target_currency):,.2f}")
    margin.metric("Profit margin", f"{result['margin_pct']:.2f}%")
    break_even = "Not reached" if result["break_even_quantity"] == 0.0 else f"{result['break_even_quantity']:.2f} units"
    render_table(
        [
            ("Variable cost", f"{symbol}{currency_converter.convert_from_base(result['variable_cost'], target_currency):,.2f}"),
            ("Fixed cost", f"{symbol}{currency_converter.convert_from_base(result['fixed_cost'], target_currency):,.2f}"),
            ("Total cost", f"{symbol}{currency_converter.convert_from_base(result['total_cost'], target_currency):,.2f}"),
            ("Break-even quantity", break_even),
        ]
    )
    record_calculation("Profit Analysis", f"{result['margin_pct']:.2f}% margin", result["profit"])


def render_reports():
    st.title("Reports")
    st.caption("Calculation history for this browser session.")
    history = st.session_state.get("calculation_history", [])
    if not history:
        st.info("Run a calculator to add its summary to this report.")
        return

    render_table(
        [
            (f"{entry['time']} - {entry['module']}", entry["summary"])
            for entry in reversed(history)
        ]
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=("time", "module", "summary", "value"))
    writer.writeheader()
    writer.writerows(history)
    st.download_button("Download CSV report", output.getvalue(), "dairy-calculation-report.csv", "text/csv")


def render_analytics():
    st.title("Analytics")
    st.caption("Session-level calculation activity.")
    history = st.session_state.get("calculation_history", [])
    if not history:
        st.info("Run a calculator to generate session analytics.")
        return

    module_counts = Counter(entry["module"] for entry in history)
    total, most_used, unique = st.columns(3)
    total.metric("Calculations run", len(history))
    most_used.metric("Most used module", module_counts.most_common(1)[0][0])
    unique.metric("Modules used", len(module_counts))
    render_table([(module, f"{count} run(s)") for module, count in module_counts.most_common()])


def render_settings():
    st.title("Settings")
    st.caption("Suite settings and calculation notes.")
    st.info(
        "Each process calculator exposes the recovery, composition, or moisture assumption "
        "that drives its estimate. Update these values to match your plant specification."
    )
    st.write("Economic inputs use INR as the base currency; the cost and profit modules can display converted values.")


def open_dairy_yield_calculator():
    st.session_state["navigation_page"] = "  Dairy Yield Calculator (Existing)"


load_styles()
calc = Calculator()
curr = CurrencyConverter()

with st.sidebar:
    st.title("Dairy Process")
    st.caption("Calculator Suite")
    st.divider()
    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Calculators",
            "  Dairy Yield Calculator (Existing)",
            "  Milk Standardization",
            "  Paneer Yield",
            "  Butter Calculator",
            "  Ghee Calculator",
            "  Cheese Calculator",
            "  Production Cost",
            "  Profit Analysis",
            "Market Opportunities",
            "Business Opportunity",
            "Dairy Industry Analysis",
            "Prices",
            "Reports",
            "Analytics",
            "Settings",
        ],
        label_visibility="collapsed",
        key="navigation_page",
    )

if page == "  Dairy Yield Calculator (Existing)":
    render_dairy_yield_calculator(calc, curr)
elif page == "  Milk Standardization":
    render_milk_standardization()
elif page == "  Paneer Yield":
    render_paneer_yield()
elif page == "  Butter Calculator":
    render_butter_calculator()
elif page == "  Ghee Calculator":
    render_ghee_calculator()
elif page == "  Cheese Calculator":
    render_cheese_calculator()
elif page == "  Production Cost":
    render_production_cost(curr)
elif page == "  Profit Analysis":
    render_profit_analysis(curr)
elif page == "Market Opportunities":
    render_market_opportunities()
elif page == "Business Opportunity":
    render_business_opportunity()
elif page == "Dairy Industry Analysis":
    render_dairy_industry_analysis()
elif page == "Prices":
    render_prices()
elif page == "Reports":
    render_reports()
elif page == "Analytics":
    render_analytics()
elif page == "Settings":
    render_settings()
elif page == "Calculators":
    st.title("Calculators")
    st.write("Choose a calculator from the sidebar to start a dairy process estimate.")
else:
    st.title("Dairy Process Calculator Suite")
    st.write("A unified workspace for dairy processing, yield, cost, and profit decisions.")
    primary_action, suite_status = st.columns([2, 1])
    with primary_action:
        st.subheader("Start with the existing calculator")
        st.write(
            "Use the Dairy Yield Calculator to estimate conversion yields, "
            "input cost, output value, and net value."
        )
        st.button(
            "Open Dairy Yield Calculator",
            type="primary",
            on_click=open_dairy_yield_calculator,
        )
    with suite_status:
        st.subheader("Suite status")
        st.metric("Available calculators", "8")
        st.metric("Session calculations", len(st.session_state.get("calculation_history", [])))
