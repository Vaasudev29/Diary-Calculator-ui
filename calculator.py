import json, os
class Calculator:
    def __init__(self, conv_path='../data/conversion_data.json', cost_path='../data/cost_data.json'):
        cur_dir = os.path.dirname(__file__)
        self.conv_path = os.path.abspath(os.path.join(cur_dir, conv_path))
        self.cost_path = os.path.abspath(os.path.join(cur_dir, cost_path))
        with open(self.conv_path, 'r') as f: data = json.load(f)
        self.conversions = data['conversions']
        self.units = data['units']
        with open(self.cost_path, 'r') as f: self.costs = json.load(f)
    def get_supported_products(self): return sorted(list(self.conversions.keys()))
    def calculate_yield(self, item, qty, level=0):
        res = {}
        if level > 3: return {}
        for out, f in self.conversions.get(item, {}).items():
            y_qty = qty * f
            res[out] = {'quantity': y_qty, 'unit': self.units.get(out, 'unit')}
            res.update(self.calculate_yield(out, y_qty, level + 1))
        return res
    def calculate_costs(self, item, qty, yields):
        in_cost = self.costs.get(item, 0) * qty
        out_val = sum([self.costs.get(p, 0) * d['quantity'] for p, d in yields.items()])
        return {'total_input_cost': in_cost, 'total_output_value': out_val, 'profit_loss': out_val - in_cost}