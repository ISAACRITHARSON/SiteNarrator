import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Submit from "./pages/Submit";
import Review from "./pages/Review";
import ReportView from "./pages/ReportView";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Evaluation from "./pages/Evaluation";
import NewProject from "./pages/NewProject";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Submit />} />
        <Route path="/review" element={<Review />} />
        <Route path="/report/:reportId" element={<ReportView />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/history" element={<History />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/new-project" element={<NewProject />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
