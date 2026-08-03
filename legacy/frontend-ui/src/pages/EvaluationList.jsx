import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Input,
  Select,
  Space,
  Tag,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { evaluationApi } from '../api';

const { Text } = Typography;

const CATEGORIES = [
  { value: '역량', label: '역량' },
  { value: '성과', label: '성과' },
  { value: '태도', label: '태도' },
  { value: '전문성', label: '전문성' },
  { value: '커뮤니케이션', label: '커뮤니케이션' },
  { value: '리더십', label: '리더십' },
  { value: '문제해결력', label: '문제해결력' },
  { value: '팀워크', label: '팀워크' },
];

const STATUS_MAP = {
  draft: { color: 'default', text: '임시저장' },
  submitted: { color: 'processing', text: '제출됨' },
  completed: { color: 'success', text: '완료' },
};

const EvaluationList = () => {
  const navigate = useNavigate();
  const gridRef = useRef(null);

  const [rowData, setRowData] = useState([]);
  const [columnDefs, setColumnDefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ currentPage: 1, totalPages: 1, total: 0 });
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [stats, setStats] = useState(null);

  const fetchEvaluations = async (page = 1) => {
    setLoading(true);
    try {
      const params = {
        page,
        limit: 10,
        sort: '-createdAt',
      };
      if (searchText) params.evaluatee = searchText;
      if (categoryFilter) params.category = categoryFilter;
      if (statusFilter) params.status = statusFilter;

      const res = await evaluationApi.getAll(params);
      setRowData(res.data.data || []);
      setPagination({
        currentPage: res.data.page,
        totalPages: res.data.pages,
        total: res.data.total,
      });
    } catch (err) {
      message.error('평가 데이터를 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await evaluationApi.getStats();
      setStats(res.data.data);
    } catch (err) {
      console.error('Stats fetch error', err);
    }
  };

  useEffect(() => {
    fetchEvaluations(1);
    fetchStats();
  }, []);

  const handleSearch = () => {
    fetchEvaluations(1);
  };

  const handleReset = () => {
    setSearchText('');
    setCategoryFilter('');
    setStatusFilter('');
    fetchEvaluations(1);
  };

  const handleDelete = async (id) => {
    try {
      await evaluationApi.delete(id);
      message.success('평가 데이터가 삭제되었습니다');
      fetchEvaluations(pagination.currentPage);
    } catch (err) {
      message.error('삭제에 실패했습니다');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#52c41a';
    if (score >= 80) return '#1890ff';
    if (score >= 70) return '#faad14';
    return '#ff4d4f';
  };

  const colDefs = [
    {
      headerName: 'No',
      valueGetter: (params) => {
        return (pagination.currentPage - 1) * 10 + params.node.rowIndex + 1;
      },
      width: 60,
      checkboxSelection: false,
      sortable: false,
      filter: false,
    },
    {
      headerName: '제목',
      field: 'title',
      flex: 2,
      sortable: true,
      filter: true,
      wrapText: true,
      autoHeight: true,
    },
    {
      headerName: '평가자',
      field: 'evaluator',
      flex: 1,
      sortable: true,
      filter: true,
    },
    {
      headerName: '평가대상',
      field: 'evaluatee',
      flex: 1,
      sortable: true,
      filter: true,
    },
    {
      headerName: '항목',
      field: 'category',
      width: 100,
      sortable: true,
      filter: true,
      cellRenderer: (params) => {
        const cat = CATEGORIES.find((c) => c.value === params.value);
        return cat ? <Tag color="blue">{cat.label}</Tag> : params.value;
      },
    },
    {
      headerName: '점수',
      field: 'score',
      width: 80,
      sortable: true,
      filter: 'agNumberColumnFilter',
      cellRenderer: (params) => (
        <Text strong style={{ color: getScoreColor(params.value) }}>
          {params.value}
        </Text>
      ),
    },
    {
      headerName: '상태',
      field: 'status',
      width: 90,
      sortable: true,
      filter: true,
      cellRenderer: (params) => {
        const s = STATUS_MAP[params.value] || { color: 'default', text: params.value };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      headerName: '기한',
      field: 'dueDate',
      width: 120,
      sortable: true,
      valueFormatter: (params) => {
        return params.value ? new Date(params.value).toLocaleDateString('ko-KR') : '-';
      },
    },
    {
      headerName: '작성일',
      field: 'createdAt',
      width: 120,
      sortable: true,
      valueFormatter: (params) => {
        return params.value ? new Date(params.value).toLocaleDateString('ko-KR') : '-';
      },
    },
    {
      headerName: '작업',
      width: 100,
      sortable: false,
      filter: false,
      cellRenderer: (params) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/evaluations/${params.data._id}/edit`)}
          >
            수정
          </Button>
          <Popconfirm
            title="삭제하시겠습니까?"
            onConfirm={() => handleDelete(params.data._id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              삭제
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">평가 관리</h1>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/evaluations/create')}
        >
          평가 등록
        </Button>
      </div>

      {stats && (
        <div className="stat-cards">
          <div className="stat-card">
            <div className="label">총 평가 건수</div>
            <div className="value">
              {stats.byStatus?.reduce((sum, s) => sum + s.count, 0) || 0}
            </div>
          </div>
          <div className="stat-card">
            <div className="label">평균 점수</div>
            <div className="value">{stats.overallAverage?.toFixed(1) || 0}</div>
          </div>
          {stats.byCategory?.slice(0, 3).map((cat) => (
            <div className="stat-card" key={cat._id}>
              <div className="label">{cat._id} 평균</div>
              <div className="value">{cat.avgScore?.toFixed(1) || 0}</div>
              <div className="sub">{cat.count}건</div>
            </div>
          ))}
        </div>
      )}

      <div className="filter-bar">
        <Input
          placeholder="평가대상 검색"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 200 }}
        />
        <Select
          placeholder="평가항목"
          allowClear
          value={categoryFilter}
          onChange={setCategoryFilter}
          options={CATEGORIES}
          style={{ width: 140 }}
        />
        <Select
          placeholder="상태"
          allowClear
          value={statusFilter}
          onChange={setStatusFilter}
          options={Object.entries(STATUS_MAP).map(([value, { text }]) => ({
            value,
            label: text,
          }))}
          style={{ width: 120 }}
        />
        <Button icon={<SearchOutlined />} onClick={handleSearch}>
          검색
        </Button>
        <Button icon={<ReloadOutlined />} onClick={handleReset}>
          초기화
        </Button>
      </div>

      <div className="grid-wrapper">
        <div
          className="ag-theme-alpine"
          style={{ height: 500, width: '100%' }}
        >
          <AgGridReact
            ref={gridRef}
            rowData={rowData}
            columnDefs={colDefs}
            loading={loading}
            pagination={true}
            paginationPageSize={10}
            defaultColDef={{
              resizable: true,
              filter: true,
              floatingFilter: true,
            }}
            localeText={{
              nextPage: '다음 페이지',
              previousPage: '이전 페이지',
              rowsPerPage: '행 수:',
              searchOoo: '검색...',
              noMatches: '검색 결과가 없습니다',
            }}
            animateRows={true}
            rowSelection={'single'}
            onGridReady={() => {}}
          />
        </div>
      </div>
    </div>
  );
};

export default EvaluationList;
