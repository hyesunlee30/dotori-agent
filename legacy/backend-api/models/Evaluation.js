const mongoose = require('mongoose');

const evaluationSchema = new mongoose.Schema(
  {
    title: {
      type: String,
      required: [true, '제목을 입력해주세요'],
      trim: true,
      maxlength: [200, '제목은 200자를 넘을 수 없습니다'],
    },
    evaluator: {
      type: String,
      required: [true, '평가자를 입력해주세요'],
      trim: true,
    },
    evaluatee: {
      type: String,
      required: [true, '평가대상을 입력해주세요'],
      trim: true,
    },
    category: {
      type: String,
      required: [true, '평가항목을 선택해주세요'],
      enum: {
        values: ['역량', '성과', '태도', '전문성', '커뮤니케이션', '리더십', '문제해결력', '팀워크'],
        message: '올바른 평가항목을 선택해주세요',
      },
    },
    score: {
      type: Number,
      required: [true, '점수를 입력해주세요'],
      min: [1, '점수는 1점 이상입니다'],
      max: [100, '점수는 100점 이하입니다'],
    },
    comments: {
      type: String,
      trim: true,
      maxlength: [1000, '코멘트는 1000자를 넘을 수 없습니다'],
    },
    status: {
      type: String,
      enum: {
        values: ['draft', 'submitted', 'completed'],
        message: '올바른 상태값을 선택해주세요',
      },
      default: 'draft',
    },
    dueDate: {
      type: Date,
    },
    period: {
      start: {
        type: Date,
      },
      end: {
        type: Date,
      },
    },
  },
  {
    timestamps: true,
  }
);

evaluationSchema.index({ evaluator: 1, evaluatee: 1, category: 1 });
evaluationSchema.index({ createdAt: -1 });
evaluationSchema.index({ status: 1 });

module.exports = mongoose.model('Evaluation', evaluationSchema);
