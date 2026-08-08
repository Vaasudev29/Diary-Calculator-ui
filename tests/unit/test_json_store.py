from services.json_store import JsonStore


def test_json_store_loads_config():
    js = JsonStore()
    products = js.list_products()
    assert any(p.id == 'Milk' for p in products)
    mc = js.get_milk_composition('cow')
    assert mc is not None and mc.fat_pct
    util = js.get_utility('Electricity')
    assert util is not None and util.unit == 'kWh'
