"""Formula helpers for the Dairy Process Calculator Suite."""


def standardize_milk(
    milk_quantity,
    source_fat_pct,
    target_fat_pct,
    skim_fat_pct,
    cream_fat_pct,
):
    """Standardize milk by adding skim milk or cream."""
    source_fat = source_fat_pct / 100
    target_fat = target_fat_pct / 100
    skim_fat = skim_fat_pct / 100
    cream_fat = cream_fat_pct / 100

    if target_fat > source_fat:
        added_cream = milk_quantity * (target_fat - source_fat) / (cream_fat - target_fat)
        return {
            "method": "Cream enrichment",
            "standardized_milk": milk_quantity + added_cream,
            "cream_added": added_cream,
            "skim_added": 0.0,
            "target_fat_pct": target_fat_pct,
        }

    if target_fat < source_fat:
        added_skim = milk_quantity * (source_fat - target_fat) / (target_fat - skim_fat)
        return {
            "method": "Skim milk dilution",
            "standardized_milk": milk_quantity + added_skim,
            "cream_added": 0.0,
            "skim_added": added_skim,
            "target_fat_pct": target_fat_pct,
        }

    return {
        "method": "No adjustment required",
        "standardized_milk": milk_quantity,
        "cream_added": 0.0,
        "skim_added": 0.0,
        "target_fat_pct": target_fat_pct,
    }


def calculate_paneer_yield(
    milk_quantity,
    milk_fat_pct,
    milk_snf_pct,
    fat_recovery_pct,
    snf_recovery_pct,
    paneer_moisture_pct,
):
    """Estimate paneer yield from recovered milk solids and paneer moisture."""
    fat_solids = milk_quantity * (milk_fat_pct / 100) * (fat_recovery_pct / 100)
    snf_solids = milk_quantity * (milk_snf_pct / 100) * (snf_recovery_pct / 100)
    retained_solids = fat_solids + snf_solids
    paneer_yield = retained_solids / (1 - paneer_moisture_pct / 100)

    return {
        "paneer_yield": paneer_yield,
        "yield_pct": paneer_yield / milk_quantity * 100,
        "retained_solids": retained_solids,
        "whey": milk_quantity - paneer_yield,
    }


def calculate_butter(
    cream_quantity,
    cream_fat_pct,
    butter_fat_pct,
    fat_recovery_pct,
):
    """Estimate butter and buttermilk quantities from cream."""
    recovered_fat = cream_quantity * (cream_fat_pct / 100) * (fat_recovery_pct / 100)
    butter_yield = recovered_fat / (butter_fat_pct / 100)
    return {
        "butter_yield": butter_yield,
        "buttermilk": cream_quantity - butter_yield,
        "recovered_fat": recovered_fat,
        "yield_pct": butter_yield / cream_quantity * 100,
    }


def calculate_ghee(
    butter_quantity,
    butter_fat_pct,
    ghee_purity_pct,
    recovery_pct,
):
    """Estimate ghee yield based on butterfat recovered at target purity."""
    recovered_fat = butter_quantity * (butter_fat_pct / 100) * (recovery_pct / 100)
    ghee_yield = recovered_fat / (ghee_purity_pct / 100)
    return {
        "ghee_yield": ghee_yield,
        "residue": butter_quantity - ghee_yield,
        "recovered_fat": recovered_fat,
        "yield_pct": ghee_yield / butter_quantity * 100,
    }


def calculate_cheese_yield(
    milk_quantity,
    milk_fat_pct,
    milk_snf_pct,
    fat_recovery_pct,
    snf_recovery_pct,
    cheese_moisture_pct,
):
    """Estimate cheese yield from retained milk solids and cheese moisture."""
    fat_solids = milk_quantity * (milk_fat_pct / 100) * (fat_recovery_pct / 100)
    snf_solids = milk_quantity * (milk_snf_pct / 100) * (snf_recovery_pct / 100)
    retained_solids = fat_solids + snf_solids
    cheese_yield = retained_solids / (1 - cheese_moisture_pct / 100)
    return {
        "cheese_yield": cheese_yield,
        "yield_pct": cheese_yield / milk_quantity * 100,
        "retained_solids": retained_solids,
        "whey": milk_quantity - cheese_yield,
    }


def calculate_production_cost(
    input_quantity,
    input_cost_per_unit,
    labor_cost,
    utilities_cost,
    packaging_cost,
    overhead_pct,
    output_quantity,
):
    """Calculate process cost from variable and percentage overhead costs."""
    material_cost = input_quantity * input_cost_per_unit
    direct_cost = material_cost + labor_cost + utilities_cost + packaging_cost
    overhead_cost = direct_cost * (overhead_pct / 100)
    total_cost = direct_cost + overhead_cost
    return {
        "material_cost": material_cost,
        "labor_cost": labor_cost,
        "utilities_cost": utilities_cost,
        "packaging_cost": packaging_cost,
        "overhead_cost": overhead_cost,
        "total_cost": total_cost,
        "cost_per_output_unit": total_cost / output_quantity,
    }


def calculate_profit(
    sales_quantity,
    selling_price_per_unit,
    variable_cost_per_unit,
    fixed_cost,
):
    """Calculate revenue, profit, margin, and break-even quantity."""
    revenue = sales_quantity * selling_price_per_unit
    variable_cost = sales_quantity * variable_cost_per_unit
    total_cost = variable_cost + fixed_cost
    contribution_per_unit = selling_price_per_unit - variable_cost_per_unit
    profit = revenue - total_cost
    return {
        "revenue": revenue,
        "variable_cost": variable_cost,
        "fixed_cost": fixed_cost,
        "total_cost": total_cost,
        "profit": profit,
        "margin_pct": profit / revenue * 100 if revenue else 0.0,
        "break_even_quantity": fixed_cost / contribution_per_unit if contribution_per_unit else 0.0,
    }
