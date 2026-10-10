export interface Reading {
  id: number;
  meter_id: number;
  reading_date: string; // ISO YYYY-MM-DD
  value: number;
}

export interface Tariff {
  id: number;
  meter_id: number;
  name: string | null;
  price_per_unit: number;
  base_price_monthly: number | null;
  valid_from: string;
}

export type ForecastMethod = 'calculated' | 'seasonal' | 'weighted';

export interface ForecastCost {
  method: ForecastMethod;
  consumption: number | null;
  cost: number | null;
}

export interface MeterStats {
  avg_3month: number | null;
  pred_weighted: number | null;
  pred_seasonal: number | null;
  pred_calculated: number | null;
  yearly_consumption: number | null;
  yearly_cost: number | null;
  forecast_cost: ForecastCost | null;
}

export interface Meter {
  id: number;
  name: string;
  unit: string;
  serial_number: string | null;
  weather_overlay: boolean;
}

export interface DashboardMeter extends Meter {
  last_reading: Reading | null;
  stats: MeterStats;
  current_tariff: Tariff | null;
}

export interface DashboardResponse {
  meters: DashboardMeter[];
}

export interface ConsumptionPoint {
  year: number;
  month: number;
  label: string;
  consumption: number | null;
}

export interface ConsumptionResponse {
  meter: Meter;
  series: ConsumptionPoint[];
}

export interface ReadingsResponse {
  meter: Meter;
  total: number;
  readings: Reading[];
}

export interface CostPoint {
  year: number;
  month: number;
  label: string;
  consumption: number | null;
  cost: number | null;
  tariff_id: number | null;
  price_per_unit: number | null;
  base_price_monthly: number | null;
}

export interface CostsResponse {
  meter: Meter;
  series: CostPoint[];
  yearly_cost: number | null;
  forecast: ForecastCost | null;
}

export interface YearComparisonValue {
  consumption: number | null;
  cost: number | null;
}

export interface YearComparisonMonth {
  month: number;
  label_short: string;
  current: YearComparisonValue;
  previous: YearComparisonValue;
  deviation_pct: number | null;
  is_current_month: boolean;
}

export interface YearComparisonResponse {
  meter: Meter;
  year: number;
  previous_year: number;
  months: YearComparisonMonth[];
  totals: {
    current: number | null;
    previous: number | null;
    deviation_pct: number | null;
  };
}

export interface WeatherPoint {
  year: number;
  month: number;
  label: string;
  consumption: number | null;
  temp_min: number | null;
  temp_avg: number | null;
  temp_max: number | null;
  hgt: number | null;
  consumption_per_hgt: number | null;
}

export interface WeatherResponse {
  meter: Meter;
  series: WeatherPoint[];
}
