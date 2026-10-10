import type { Meter } from '../api/types';

interface MeterTabsProps {
  meters: Meter[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function MeterTabs({ meters, selectedId, onSelect }: MeterTabsProps) {
  return (
    <div className="meter-tabs" role="tablist" aria-label="Zähler auswählen">
      {meters.map((meter) => (
        <button
          key={meter.id}
          type="button"
          role="tab"
          aria-selected={meter.id === selectedId}
          className={meter.id === selectedId ? 'active' : ''}
          onClick={() => onSelect(meter.id)}
        >
          {meter.name}
        </button>
      ))}
    </div>
  );
}
