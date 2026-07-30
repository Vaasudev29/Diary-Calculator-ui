import json, os
class CurrencyConverter:
    def __init__(self, path='currency_settings.json'):
        self.path = os.path.join(os.path.dirname(__file__), path)
        self.exchange_rates = {'INR': 1.0, 'USD': 0.012, 'EUR': 0.011, 'GBP': 0.0094, 'IDR': 180.0, 'AED': 0.044, 'SAR': 0.045, 'SGD': 0.016, 'MYR': 0.056}
        self.currency_symbols = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'IDR': 'Rp', 'AED': 'د.إ', 'SAR': '﷼', 'SGD': 'S$', 'MYR': 'RM'}
    def convert_from_base(self, val, target): return val * self.exchange_rates.get(target, 1.0)
    def get_currency_symbol(self, code): return self.currency_symbols.get(code, '$')