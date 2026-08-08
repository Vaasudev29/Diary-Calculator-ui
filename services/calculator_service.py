from __future__ import annotations

from typing import Optional, Dict, Any
from decimal import Decimal

from services.json_store import JsonStore
from calculators.cheese_yield_detailed import DetailedCheeseYieldCalculator
from calculators.production_cost import ProductionCostCalculator
from models.ingredient import Ingredient
from models.batch import Batch
from models.product import Product
from models.utility import Utility


class CalculatorOrchestrator:
    def __init__(self, repository: Optional[JsonStore] = None):
        self.repository = repository or JsonStore()
        self.cheese_calc = DetailedCheeseYieldCalculator(repository=self.repository)
        self.cost_calc = ProductionCostCalculator(repository=self.repository)

    def produce_cheese(self, feed_milk_type: str, batch_size_l: Decimal, target_moisture_pct: Decimal,
                       labor_cost: Optional[Decimal] = None, overhead: Optional[Decimal] = None,
                       whey_processing_overrides: Optional[Dict[str, Any]] = None,
                       whey_valuation_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # No-op patch to trigger file rewrite
        # Step 1: yield calculation
        yield_res = self.cheese_calc.run(feed_milk_type=feed_milk_type, batch_size=Decimal(batch_size_l), target_moisture_pct=Decimal(target_moisture_pct))
        if not yield_res.success:
            raise RuntimeError(f'Cheese yield calculation failed: {yield_res.errors}')
        ydata = yield_res.data

        # Step 2: prepare batch for costing
        milk_product = self.repository.get_product('Milk')
        cheese_product = self.repository.get_product('Cheese') or Product(id='Cheese', name='Cheese')

        milk_ing = Ingredient(product=milk_product, quantity=Decimal(batch_size_l), unit=milk_product.unit)

        # Use repository utilities as process utilities
        utils = []
        for u in self.repository.list_utilities():
            # clone utility; assume consumption_per_batch scaled per 1000 L base? For now use as-is
            utils.append(Utility(name=u.name, unit=u.unit, cost_per_unit=u.cost_per_unit, consumption_per_batch=u.consumption_per_batch))

        batch = Batch(id='cheese_batch_1', product=cheese_product, input_materials=[milk_ing], utilities=utils, batch_size=Decimal(batch_size_l))

        # Step 3: cost calculation
        cost_res = self.cost_calc.run(batch=batch, labor_cost=labor_cost, overhead=overhead)
        if not cost_res.success:
            raise RuntimeError(f'Cost calculation failed: {cost_res.errors}')
        pc = cost_res.data

        # Step 4: compute cost per kg of cheese and apply whey credit if available
        cheese_mass = Decimal(str(ydata.get('cheese_mass_kg'))) if ydata.get('cheese_mass_kg') is not None else Decimal('0')
        gross_total_cost = Decimal(pc.total_cost)
        total_cost = gross_total_cost

        # Whey credit: compute whey volume and solids
        whey_credit = Decimal('0')
        whey_vol = Decimal(str(ydata.get('whey_volume_l'))) if ydata.get('whey_volume_l') is not None else Decimal('0')
        whey_comp = ydata.get('whey_composition', {})
        whey_solids = Decimal('0')
        try:
            whey_solids = Decimal(str(whey_comp.get('protein_kg', 0))) + Decimal(str(whey_comp.get('lactose_kg', 0))) + Decimal(str(whey_comp.get('other_snf_kg', 0)))
        except Exception:
            whey_solids = Decimal('0')

        # valuation preferences
        whey_val_settings = (self.repository.get_standard('whey_valuation') if self.repository else None) or getattr(self.repository, '_standards', {}).get('whey_valuation', {})
        # apply per-batch overrides for valuation
        if whey_valuation_overrides:
            wvs = dict(whey_val_settings or {})
            wvs.update(whey_valuation_overrides)
            whey_val_settings = wvs
        price_protein = Decimal(whey_val_settings.get('price_per_kg_protein')) if whey_val_settings and whey_val_settings.get('price_per_kg_protein') is not None else None
        price_lactose = Decimal(whey_val_settings.get('price_per_kg_lactose')) if whey_val_settings and whey_val_settings.get('price_per_kg_lactose') is not None else None
        price_other = Decimal(whey_val_settings.get('price_per_kg_other')) if whey_val_settings and whey_val_settings.get('price_per_kg_other') is not None else None
        price_per_kg_solid = Decimal(whey_val_settings.get('price_per_kg_solid')) if whey_val_settings and whey_val_settings.get('price_per_kg_solid') is not None else None

        if (price_protein is not None or price_lactose is not None or price_other is not None) and whey_solids > 0:
            p_prot = price_protein or Decimal('0')
            p_lac = price_lactose or Decimal('0')
            p_oth = price_other or Decimal('0')
            whey_credit = (p_prot * Decimal(str(whey_comp.get('protein_kg', 0)))) + (p_lac * Decimal(str(whey_comp.get('lactose_kg', 0)))) + (p_oth * Decimal(str(whey_comp.get('other_snf_kg', 0))))
            total_cost = total_cost - whey_credit
        elif price_per_kg_solid is not None and whey_solids > 0:
            whey_credit = price_per_kg_solid * whey_solids
            total_cost = total_cost - whey_credit
        else:
            whey_product = self.repository.get_product('Whey') if self.repository else None
            if whey_product is not None and whey_vol > 0:
                whey_price = Decimal(whey_product.cost_per_unit)
                whey_credit = whey_price * whey_vol
                total_cost = total_cost - whey_credit

        # Whey processing cost adjustments
        wp = (self.repository.get_standard('whey_processing') if self.repository else None) or getattr(self.repository, '_standards', {}).get('whey_processing', {})
        # apply per-batch overrides if provided
        if whey_processing_overrides:
            # create a shallow copy then update
            wp = dict(wp or {})
            wp.update(whey_processing_overrides)
        processing_cost = Decimal('0')
        if wp and wp.get('enabled'):
            try:
                cost_per_kg_solid = Decimal(str(wp.get('processing_cost_per_kg_solid', 0)))
                cost_per_liter = Decimal(str(wp.get('processing_cost_per_liter', 0)))
                fixed_cost = Decimal(str(wp.get('fixed_cost_per_batch', 0)))
            except Exception:
                cost_per_kg_solid = Decimal('0')
                cost_per_liter = Decimal('0')
                fixed_cost = Decimal('0')

            if whey_solids > 0 and cost_per_kg_solid > 0:
                processing_cost = (cost_per_kg_solid * whey_solids) + fixed_cost
            elif whey_vol > 0 and cost_per_liter > 0:
                processing_cost = (cost_per_liter * whey_vol) + fixed_cost
            else:
                processing_cost = fixed_cost

            # Processing cost reduces net credit (add processing cost to total cost)
            total_cost = total_cost + processing_cost

        cost_per_kg = (total_cost / cheese_mass) if cheese_mass != 0 else None

        return {
            'yield': ydata,
            'production_cost': {
                'material_cost': float(pc.material_cost),
                'utility_cost': float(pc.utility_cost),
                'labor_cost': float(pc.labor_cost),
                'overhead': float(pc.overhead),
                'gross_total_cost': float(gross_total_cost),
                'whey_credit': float(whey_credit),
                'whey_processing_cost': float(processing_cost),
                'net_total_cost': float(total_cost),
                'cost_per_kg': float(cost_per_kg) if cost_per_kg is not None else None
            }
        }
