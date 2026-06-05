// map-server/mcaService.js
const MCA_SERVICE_URL = process.env.MCA_SERVICE_URL || 'http://localhost:8000';

async function forwardRequest(req, res, path) {
  const url = `${MCA_SERVICE_URL}${path}`;
  const headers = { ...req.headers };
  delete headers.host;
  delete headers['content-length']; // пусть fetch сам установит

  const fetchOptions = {
    method: req.method,
    headers,
    body: (req.method !== 'GET' && req.method !== 'HEAD') ? JSON.stringify(req.body) : undefined,
  };

  try {
    const response = await fetch(url, fetchOptions);
    // Устанавливаем статус
    res.status(response.status);
    // Копируем заголовки (кроме некоторых служебных)
    for (const [key, value] of response.headers.entries()) {
      if (key !== 'content-encoding' && key !== 'content-length') {
        res.setHeader(key, value);
      }
    }
    // Получаем тело ответа как ArrayBuffer и отправляем
    const arrayBuffer = await response.arrayBuffer();
    res.send(Buffer.from(arrayBuffer));
  } catch (err) {
    console.error(`MCA proxy error: ${err.message}`);
    res.status(503).json({ error: 'MCA service unavailable', details: err.message });
  }
}

export default function mcaService(app) {
  app.get('/api/mca/projects', (req, res) => forwardRequest(req, res, '/projects'));
  app.post('/api/mca/projects', (req, res) => forwardRequest(req, res, '/projects'));
  app.post('/api/mca/projects/:projectId/criteria', (req, res) =>
    forwardRequest(req, res, `/projects/${req.params.projectId}/criteria`)
  );
  app.post('/api/mca/projects/:projectId/run', (req, res) =>
    forwardRequest(req, res, `/projects/${req.params.projectId}/run`)
  );
  app.get('/api/mca/task/:taskId', (req, res) =>
    forwardRequest(req, res, `/task/${req.params.taskId}`)
  );
  app.get('/api/mca/results/:resultId/download', (req, res) =>
    forwardRequest(req, res, `/results/${req.params.resultId}/download`)
  );
}