import React, { useState, useEffect, useCallback } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';
import { ConfigProvider } from 'antd';
import koKR from 'antd/locale/ko_KR';
import EvaluationList from './pages/EvaluationList';
import EvaluationForm from './pages/EvaluationForm';
import './App.css';

const App = () => {
  return (
    <ConfigProvider locale={koKR}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/evaluations" replace />} />
          <Route path="/evaluations" element={<EvaluationList />} />
          <Route path="/evaluations/create" element={<EvaluationForm />} />
          <Route path="/evaluations/:id/edit" element={<EvaluationForm />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
