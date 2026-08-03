import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Button,
  message,
  Divider,
  Typography,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { evaluationApi } from '../api';

const { Title } = Typography;

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

const STATUS_OPTIONS = [
  { value: 'draft', label: '임시저장' },
  { value: 'submitted', label: '제출됨' },
  { value: 'completed', label: '완료' },
];

const EvaluationForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isEdit) {
      fetchEvaluation();
    }
  }, [id]);

  const fetchEvaluation = async () => {
    setLoading(true);
    try {
      const res = await evaluationApi.getById(id);
      const data = res.data.data;
      form.setFieldsValue({
        title: data.title,
        evaluator: data.evaluator,
        evaluatee: data.evaluatee,
        category: data.category,
        score: data.score,
        comments: data.comments,
        status: data.status,
        dueDate: data.dueDate ? dayjs(data.dueDate) : null,
        periodStart: data.period?.start ? dayjs(data.period.start) : null,
        periodEnd: data.period?.end ? dayjs(data.period.end) : null,
      });
    } catch (err) {
      message.error('평가 데이터를 불러오는데 실패했습니다');
      navigate('/evaluations');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      const submitData = {
        ...values,
        dueDate: values.dueDate ? values.dueDate.toDate() : undefined,
        period: {
          start: values.periodStart ? values.periodStart.toDate() : undefined,
          end: values.periodEnd ? values.periodEnd.toDate() : undefined,
        },
      };
      if (!submitData.period.start) delete submitData.period.start;
      if (!submitData.period.end) delete submitData.period.end;

      if (isEdit) {
        await evaluationApi.update(id, submitData);
        message.success('평가가 수정되었습니다');
      } else {
        await evaluationApi.create(submitData);
        message.success('평가가 등록되었습니다');
      }
      navigate('/evaluations');
    } catch (err) {
      message.error(isEdit ? '수정에 실패했습니다' : '등록에 실패했습니다');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    navigate('/evaluations');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          {isEdit ? '평가 수정' : '평가 등록'}
        </h1>
        <Button icon={<ArrowLeftOutlined />} onClick={handleCancel}>
          목록으로
        </Button>
      </div>

      <div className="form-wrapper">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark="optional"
        >
          <div className="form-section">
            <Title level={5} className="form-section-title">기본 정보</Title>
            <Form.Item
              label="제목"
              name="title"
              rules={[{ required: true, message: '제목을 입력해주세요' }]}
            >
              <Input placeholder="평가 제목을 입력해주세요" maxLength={200} showCount />
            </Form.Item>

            <Form.Item
              label="평가자"
              name="evaluator"
              rules={[{ required: true, message: '평가자를 입력해주세요' }]}
            >
              <Input placeholder="평가자 이름을 입력해주세요" />
            </Form.Item>

            <Form.Item
              label="평가대상"
              name="evaluatee"
              rules={[{ required: true, message: '평가대상을 입력해주세요' }]}
            >
              <Input placeholder="평가대상 이름을 입력해주세요" />
            </Form.Item>

            <Form.Item
              label="평가항목"
              name="category"
              rules={[{ required: true, message: '평가항목을 선택해주세요' }]}
            >
              <Select placeholder="평가항목을 선택해주세요" options={CATEGORIES} />
            </Form.Item>
          </div>

          <Divider />

          <div className="form-section">
            <Title level={5} className="form-section-title">평가 내용</Title>
            <Form.Item
              label="점수"
              name="score"
              rules={[{ required: true, message: '점수를 입력해주세요' }]}
            >
              <InputNumber
                min={1}
                max={100}
                placeholder="1~100 점수를 입력해주세요"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              label="상태"
              name="status"
              initialValue="draft"
            >
              <Select options={STATUS_OPTIONS} />
            </Form.Item>

            <Form.Item
              label="코멘트"
              name="comments"
            >
              <Input.TextArea
                rows={4}
                placeholder="평가 코멘트를 입력해주세요"
                maxLength={1000}
                showCount
              />
            </Form.Item>
          </div>

          <Divider />

          <div className="form-section">
            <Title level={5} className="form-section-title">일정</Title>
            <Form.Item label="기한" name="dueDate">
              <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
            </Form.Item>

            <Form.Item label="평가 기간">
              <Form.Item
                name="periodStart"
                noStyle
                rules={[{ type: 'object', message: '시작일을 선택해주세요' }]}
              >
                <DatePicker
                  style={{ width: 'calc(50% - 8px)' }}
                  format="YYYY-MM-DD"
                  placeholder="시작일"
                />
              </Form.Item>
              <span style={{ margin: '0 8px' }}>~</span>
              <Form.Item
                name="periodEnd"
                noStyle
                rules={[{ type: 'object', message: '종료일을 선택해주세요' }]}
              >
                <DatePicker
                  style={{ width: 'calc(50% - 8px)' }}
                  format="YYYY-MM-DD"
                  placeholder="종료일"
                />
              </Form.Item>
            </Form.Item>
          </div>

          <Divider />

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
                size="large"
              >
                {isEdit ? '수정하기' : '등록하기'}
              </Button>
              <Button size="large" onClick={handleCancel}>
                취소
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

export default EvaluationForm;
