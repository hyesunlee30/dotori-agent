const Evaluation = require('../models/Evaluation');

// @desc    Get all evaluations
// @route   GET /api/evaluations
// @access  Public
const getEvaluations = async (req, res) => {
  try {
    const {
      page = 1,
      limit = 10,
      sort = '-createdAt',
      category,
      status,
      evaluator,
      evaluatee,
      minScore,
      maxScore,
    } = req.query;

    const query = {};
    if (category) query.category = category;
    if (status) query.status = status;
    if (evaluator) query.evaluator = { $regex: evaluator, $options: 'i' };
    if (evaluatee) query.evaluatee = { $regex: evaluatee, $options: 'i' };
    if (minScore || maxScore) {
      query.score = {};
      if (minScore) query.score.$gte = Number(minScore);
      if (maxScore) query.score.$lte = Number(maxScore);
    }

    const skip = (Number(page) - 1) * Number(limit);
    const evaluations = await Evaluation.find(query)
      .sort(sort)
      .skip(skip)
      .limit(Number(limit));

    const total = await Evaluation.countDocuments(query);

    res.status(200).json({
      success: true,
      count: evaluations.length,
      total,
      page: Number(page),
      pages: Math.ceil(total / Number(limit)),
      data: evaluations,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다',
      error: error.message,
    });
  }
};

// @desc    Get single evaluation
// @route   GET /api/evaluations/:id
// @access  Public
const getEvaluation = async (req, res) => {
  try {
    const evaluation = await Evaluation.findById(req.params.id);
    if (!evaluation) {
      return res.status(404).json({
        success: false,
        message: '평가 데이터를 찾을 수 없습니다',
      });
    }
    res.status(200).json({
      success: true,
      data: evaluation,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다',
      error: error.message,
    });
  }
};

// @desc    Create new evaluation
// @route   POST /api/evaluations
// @access  Public
const createEvaluation = async (req, res) => {
  try {
    const evaluation = await Evaluation.create(req.body);
    res.status(201).json({
      success: true,
      data: evaluation,
    });
  } catch (error) {
    res.status(400).json({
      success: false,
      message: '오류가 발생했습니다',
      error: error.message,
    });
  }
};

// @desc    Update evaluation
// @route   PUT /api/evaluations/:id
// @access  Public
const updateEvaluation = async (req, res) => {
  try {
    const evaluation = await Evaluation.findByIdAndUpdate(
      req.params.id,
      req.body,
      {
        new: true,
        runValidators: true,
      }
    );
    if (!evaluation) {
      return res.status(404).json({
        success: false,
        message: '평가 데이터를 찾을 수 없습니다',
      });
    }
    res.status(200).json({
      success: true,
      data: evaluation,
    });
  } catch (error) {
    res.status(400).json({
      success: false,
      message: '오류가 발생했습니다',
      error: error.message,
    });
  }
};

// @desc    Delete evaluation
// @route   DELETE /api/evaluations/:id
// @access  Public
const deleteEvaluation = async (req, res) => {
  try {
    const evaluation = await Evaluation.findByIdAndDelete(req.params.id);
    if (!evaluation) {
      return res.status(404).json({
        success: false,
        message: '평가 데이터를 찾을 수 없습니다',
      });
    }
    res.status(200).json({
      success: true,
      message: '평가 데이터가 삭제되었습니다',
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다',
      error: error.message,
    });
  }
};

// @desc    Get statistics
// @route   GET /api/evaluations/stats
// @access  Public
const getStats = async (req, res) => {
  try {
    const stats = await Evaluation.aggregate([
      {
        $group: {
          _id: '$category',
          avgScore: { $avg: '$score' },
          count: { $sum: 1 },
          minScore: { $min: '$score' },
          maxScore: { $max: '$score' },
        },
      },
      { $sort: { avgScore: -1 } },
    ]);

    const overallAvg = await Evaluation.aggregate([
      { $group: { _id: null, avgScore: { $avg: '$score' } } },
    ]);

    const statusCount = await Evaluation.aggregate([
      { $group: { _id: '$status', count: { $sum: 1 } } },
    ]);

    res.status(200).json({
      success: true,
      data: {
        byCategory: stats,
        overallAverage: overallAvg[0]?.avgScore || 0,
        byStatus: statusCount,
      },
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: '서버 오류가 발생했습니다',
      error: error.message,
    });
  }
};

module.exports = {
  getEvaluations,
  getEvaluation,
  createEvaluation,
  updateEvaluation,
  deleteEvaluation,
  getStats,
};
