const express = require('express');
const router = express.Router();
const {
  getEvaluations,
  getEvaluation,
  createEvaluation,
  updateEvaluation,
  deleteEvaluation,
  getStats,
} = require('../controllers/evaluationController');

router.route('/')
  .get(getEvaluations)
  .post(createEvaluation);

router.get('/stats', getStats);

router.route('/:id')
  .get(getEvaluation)
  .put(updateEvaluation)
  .delete(deleteEvaluation);

module.exports = router;
