import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ChatPage         from './pages/ChatPage'
import AdminLogin       from './pages/AdminLogin'
import AdminLayout      from './pages/AdminLayout'
import Dashboard        from './pages/Dashboard'
import FAQManager       from './pages/FAQManager'
import KnowledgeManager from './pages/KnowledgeManager'
import UnansweredPage   from './pages/UnansweredPage'
import CompanyManager   from './pages/CompanyManager'
import EndpointManager  from './pages/EndpointManager'
import CacheManager     from './pages/CacheManager'
import AISettings       from './pages/AISettings'
import ProtectedRoute   from './components/ProtectedRoute'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<ChatPage/>}/>
          <Route path="/admin/login" element={<AdminLogin/>}/>
          <Route path="/admin" element={<ProtectedRoute><AdminLayout/></ProtectedRoute>}>
            <Route index element={<Navigate to="dashboard" replace/>}/>
            <Route path="dashboard"  element={<Dashboard/>}/>
            <Route path="faq"        element={<FAQManager/>}/>
            <Route path="knowledge"  element={<KnowledgeManager/>}/>
            <Route path="companies"  element={<CompanyManager/>}/>
            <Route path="endpoints"  element={<EndpointManager/>}/>
            <Route path="cache"        element={<CacheManager/>}/>
            <Route path="unanswered"   element={<UnansweredPage/>}/>
            <Route path="ai-settings"  element={<AISettings/>}/>
          </Route>
          <Route path="*" element={<Navigate to="/" replace/>}/>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
