import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import EvaluationPage from './pages/EvaluationPage';
import VendorDashboard from './pages/VendorDashboard';
import VendorDetailPage from './pages/VendorDetailPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/upload"
                element={<ProtectedRoute><UploadPage /></ProtectedRoute>}
              />
              <Route
                path="/chat"
                element={<ProtectedRoute><ChatPage /></ProtectedRoute>}
              />
              <Route
                path="/admin"
                element={<ProtectedRoute><AdminPage /></ProtectedRoute>}
              />
              <Route
                path="/evaluate"
                element={<ProtectedRoute><EvaluationPage /></ProtectedRoute>}
              />
              <Route
                path="/vendors"
                element={<ProtectedRoute><VendorDashboard /></ProtectedRoute>}
              />
              <Route
                path="/vendors/:id"
                element={<ProtectedRoute><VendorDetailPage /></ProtectedRoute>}
              />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </Router>
  );
}
