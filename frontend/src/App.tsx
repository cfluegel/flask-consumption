import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { MeterDetailPage } from './pages/MeterDetailPage';
import { ReadingFormPage } from './pages/ReadingFormPage';
import { CostsPage } from './pages/CostsPage';
import { TariffsPage } from './pages/TariffsPage';
import { YearComparisonPage } from './pages/YearComparisonPage';
import { GraphDetailPage } from './pages/GraphDetailPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/zaehler/:id" element={<MeterDetailPage />} />
          <Route path="/ablesung/neu" element={<ReadingFormPage />} />
          <Route path="/kosten" element={<CostsPage />} />
          <Route path="/tarife" element={<TariffsPage />} />
          <Route path="/vergleich" element={<YearComparisonPage />} />
          <Route path="/grafiken/:id" element={<GraphDetailPage />} />
          <Route path="/einstellungen" element={<SettingsPage />} />
          <Route path="*" element={<div className="empty-state">Seite nicht gefunden</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
