require('dotenv').config();
const express = require('express');
const cors = require('cors');
const connectDB = require('./config/db');
const evaluationRoutes = require('./routes/evaluations');

const app = express();

connectDB();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/api/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
  });
});

app.use('/api/evaluations', evaluationRoutes);

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    message: '서버 오류가 발생했습니다',
  });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
