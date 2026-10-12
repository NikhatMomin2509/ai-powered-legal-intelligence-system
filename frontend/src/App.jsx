import { Routes, Route } from "react-router-dom";
import Shell from "./components/layout/Shell";
import Dashboard from "./pages/Dashboard";
import IssueAnalyzer from "./pages/IssueAnalyzer";
import DocumentAnalyzer from "./pages/DocumentAnalyzer";
import History from "./pages/History";
import Login from "./pages/Login";
import Register from "./pages/Register";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/issue-analyzer" element={<IssueAnalyzer />} />
        <Route path="/case/:caseId" element={<IssueAnalyzer />} />
        <Route path="/document-analyzer" element={<DocumentAnalyzer />} />
        <Route path="/history" element={<History />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Routes>
    </Shell>
  );
}
