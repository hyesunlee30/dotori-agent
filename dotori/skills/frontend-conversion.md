# Frontend Conversion Skill: React SPA to FSD Architecture

## Overview

This skill defines the conversion rules for transforming React SPA (Vite + Ant Design) frontend code to Feature-Sliced Design (FSD) architecture.

## FSD Folder Structure

```
src/
├── app/                          # App entry point
│   ├── providers/
│   │   └── AppProviders.tsx
│   ├── router/
│   │   └── AppRouter.tsx
│   └── App.tsx
├── features/
│   └── evaluations/
│       ├── ui/
│       │   ├── EvaluationList.tsx
│       │   ├── EvaluationForm.tsx
│       │   ├── EvaluationStats.tsx
│       │   └── EvaluationStatusTag.tsx
│       ├── api/
│       │   └── evaluationApi.ts
│       ├── model/
│       │   ├── types.ts
│       │   └── selectors.ts
│       └── hooks/
│           └── useEvaluations.ts
├── entities/
│   └── evaluation/
│       ├── model/
│       │   ├── types.ts
│       │   └── helpers.ts
│       └── ui/
│           ├── EvaluationCard.tsx
│           └── EvaluationSummary.tsx
├── shared/
│   ├── api/
│   │   └── axios.ts
│   ├── ui/
│   │   ├── components/
│   │   │   ├── PageHeader.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   └── EmptyState.tsx
│   │   └── hooks/
│   │       └── usePageTranslation.ts
│   ├── lib/
│   │   └── dayjs.ts
│   └── constants/
│       └── apiEndpoints.ts
└── widgets/
    └── evaluation/
        ├── EvaluationDashboard.tsx
        └── EvaluationFilters.tsx
```

## Conversion Rules

### Export Style

| Legacy (React SPA) | FSD (Converted) |
|--------------------|-----------------|
| `export default function Component()` | `export const Component = () => {}` |
| `import Component from './Component'` | `import { Component } from '@/features/...'` |

### API Client

| Legacy | FSD |
|--------|-----|
| `src/api/index.js` (Axios per-page) | `shared/api/axios.ts` (single instance) |
| Hardcoded `http://localhost:5000/api` | Environment variable + `shared/constants/apiEndpoints.ts` |

### Component Organization

| Legacy Location | FSD Location |
|-----------------|--------------|
| `src/pages/EvaluationList.jsx` | `features/evaluations/ui/EvaluationList.tsx` |
| `src/pages/EvaluationForm.jsx` | `features/evaluations/ui/EvaluationForm.tsx` |
| `src/App.jsx` (Router) | `app/router/AppRouter.tsx` |
| `src/main.jsx` | `app/main.tsx` |

## Ant Design Conversion Notes

### Component Usage Rules

| Legacy (Avoid) | FSD (Required) |
|----------------|----------------|
| `<Tag size="small">` | `<Tag>` (no size prop) |
| `<Input.Group>` | `<Space.Compact>` |
| `message.success()` (direct) | `const { message } = App.useApp(); message.success()` |
| `modal.confirm()` (direct) | `const { modal } = App.useApp(); modal.confirm()` |

### Form Pattern

```tsx
// Legacy: Direct antd Form usage
import { Form, Input, Select, Button, message } from 'antd';

const EvaluationForm = () => {
  const [form] = Form.useForm();
  const handleSubmit = async (values) => {
    message.success('등록되었습니다');
  };
  return <Form form={form} onFinish={handleSubmit}>...</Form>;
};

// FSD: With App.useApp() hook extraction
import { App } from 'antd';
import { usePageTranslation } from '@/shared/ui/hooks/usePageTranslation';

const EvaluationForm = () => {
  const { form } = Form.useForm();
  const { message } = App.useApp();
  const { t } = usePageTranslation('evaluation');
  
  const handleSubmit = async (values) => {
    message.success(t('registrationSuccess'));
  };
  return <Form form={form} onFinish={handleSubmit}>...</Form>;
};
```

## AG Grid Conversion

### Column Definition

```tsx
// Legacy: Direct column config
const columns = [
  { headerName: '제목', field: 'title', flex: 1 },
  { headerName: '점수', field: 'score', width: 80 },
];

// FSD: Shared component with typed columns
import { ColumnDef } from '@ag-grid-community/react';
import { Evaluation } from '@/entities/evaluation/model/types';

export const evaluationColumns: ColumnDef<Evaluation>[] = [
  { field: 'title', flex: 1, headerName: '제목' },
  { field: 'score', width: 80, headerName: '점수' },
  { field: 'category', width: 100, headerName: '평가항목' },
  { field: 'status', width: 100, headerName: '상태' },
];
```

### Grid Configuration

```tsx
// Legacy: Inline theme + className
<AgGridReact theme={theme} className="custom-grid" ... />

// FSD: CSS class only (no theme + className together)
import '@/shared/ui/components/AgGridTheme.css';
<AgGridReact className="ag-theme-alpine" ... />
```

## Internationalization

### usePageTranslation Hook

```tsx
// Legacy: Hardcoded Korean strings
<h1>평가 목록</h1>
<Form.Item label="제목">{/* ... */}</Form.Item>

// FSD: Translation hook required
const { t } = usePageTranslation('evaluation');
<h1>{t('listTitle')}</h1>
<Form.Item label={t('titleLabel')}>{/* ... */}</Form.Item>
```

### Translation Key Format

```
{t("key", "한국어")}
```

## Import Rules (FSD Strict)

| Layer | Can Import From |
|-------|----------------|
| `app` | `shared`, `entities`, `features`, `widgets` |
| `widgets` | `shared`, `entities`, `features` |
| `features` | `shared`, `entities` |
| `entities` | `shared` |
| `shared` | (nothing - lowest level) |

**Forbidden:** Lower layers cannot import from higher layers.

## Type Definitions

### Entity Types (entities/evaluation/model/types.ts)

```typescript
export interface Evaluation {
  id: string;
  title: string;
  category: Category;
  score: number;
  status: EvaluationStatus;
  evaluator: string;
  evaluatee: string;
  createdAt: string;
  updatedAt: string;
}

export enum Category {
  역량 = '역량',
  성과 = '성과',
  태도 = '태도',
  전문성 = '전문성',
  커뮤니케이션 = '커뮤니케이션',
  리더십 = '리더십',
  문제해결력 = '문제해결력',
  팀워크 = '팀워크',
}

export enum EvaluationStatus {
  Draft = 'draft',
  Submitted = 'submitted',
  Completed = 'completed',
}
```

### Feature Types (features/evaluations/model/types.ts)

```typescript
export interface EvaluationListParams {
  page: number;
  size: number;
  searchText?: string;
  category?: string;
  status?: string;
}

export interface EvaluationFormData {
  title: string;
  category: Category;
  score: number;
  evaluator: string;
  evaluatee: string;
}

export interface PageResponse<T> {
  data: T[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}
```

## API Client Pattern

```typescript
// shared/api/axios.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  headers: { 'Content-Type': 'application/json' },
});

// features/evaluations/api/evaluationApi.ts
import { apiClient } from '@/shared/api/axios';
import type { Evaluation, EvaluationListParams } from '@/entities/evaluation/model/types';
import type { PageResponse } from '@/features/evaluations/model/types';

export const evaluationApi = {
  getAll: (params: EvaluationListParams) =>
    apiClient.get<PageResponse<Evaluation>>('/evaluations', { params }),

  getById: (id: string) =>
    apiClient.get<{ data: Evaluation }>(`/evaluations/${id}`),

  create: (data: EvaluationFormData) =>
    apiClient.post<{ data: Evaluation }>('/evaluations', data),

  update: (id: string, data: EvaluationFormData) =>
    apiClient.put<{ data: Evaluation }>(`/evaluations/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/evaluations/${id}`),

  getStats: () =>
    apiClient.get<{ data: unknown }>('/evaluations/stats'),
};
```

## Hook Pattern

```typescript
// features/evaluations/hooks/useEvaluations.ts
import { useState, useEffect, useCallback } from 'react';
import { evaluationApi } from '../api/evaluationApi';
import type { Evaluation, EvaluationListParams } from '@/entities/evaluation/model/types';
import type { PageResponse } from '../model/types';

export function useEvaluations(params: EvaluationListParams) {
  const [data, setData] = useState<Evaluation[]>([]);
  const [pagination, setPagination] = useState<PageResponse<Evaluation>>({
    data: [], page: 1, size: 10, total: 0, totalPages: 0,
  });
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evaluationApi.getAll(params);
      const pageData = res.data.data || [];
      setData(pageData);
      setPagination({ data: pageData, ...res.data });
    } catch {
      // Error handled by UI layer
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => { fetch(); }, [fetch]);

  return { data, pagination, loading, refetch: fetch };
}
```
