import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { SettingsProvider } from "./context/SettingsContext";
import { Overview } from "./pages/Overview";
import { Optimization } from "./pages/Optimization";
import { RiskAnalysis } from "./pages/RiskAnalysis";
import { EfficientFrontier } from "./pages/EfficientFrontier";
import { QuantumLab } from "./pages/QuantumLab";
import { Backtesting } from "./pages/Backtesting";
import { MarketData } from "./pages/MarketData";
import { NewsEvents } from "./pages/NewsEvents";
import { LiveTV } from "./pages/LiveTV";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
    <SettingsProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Overview />} />
            <Route path="/optimization" element={<Optimization />} />
            <Route path="/risk" element={<RiskAnalysis />} />
            <Route path="/frontier" element={<EfficientFrontier />} />
            <Route path="/quantum" element={<QuantumLab />} />
            <Route path="/backtesting" element={<Backtesting />} />
            <Route path="/market-data" element={<MarketData />} />
            <Route path="/news" element={<NewsEvents />} />
            <Route path="/live-tv" element={<LiveTV />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SettingsProvider>
  );
}
