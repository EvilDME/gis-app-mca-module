import express from 'express';
import cors from 'cors';
import pg from 'pg';
import dotenv from 'dotenv';
import jwt from 'jsonwebtoken';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRouteWorkerPool, resolveRouteWorkerSettings, RouteQueueFullError, RouteTaskTimeoutError } from './utils/RouteWorkerPool.js';

import mcaService from './mcaService.js';

dotenv.config();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const responseCache = {
    reviews: { value: null, expiresAt: 0 },
    comments: new Map(),
    vectors: new Map(),
};


app.use(cors());
app.use(express.json());

// ### ИЗМЕНЕНИЯ ДЛЯ МОДУЛЯ ###
mcaService(app);

const formatIp = (req) => {
    const forwarded = req.headers['x-forwarded-for'];
    if (typeof forwarded === 'string' && forwarded.length > 0) {
        return forwarded.split(',')[0].trim();
    }

    return req.socket.remoteAddress || 'unknown';
};

const formatUser = (req) => req.user?.username || req.user?.id || 'guest';
const shortHost = (req) => req.headers.host || 'unknown-host';

const now = () => Date.now();
const cacheGet = (entry) => (entry && entry.expiresAt > now() ? entry.value : null);
const cacheSet = (target, value, ttlMs) => {
    target.value = value;
    target.expiresAt = now() + ttlMs;
};
const cacheMapGet = (map, key) => {
    const entry = map.get(key);
    if (!entry || entry.expiresAt <= now()) {
        if (entry) map.delete(key);
        return null;
    }

    return entry.value;
};
const cacheMapSet = (map, key, value, ttlMs) => {
    map.set(key, { value, expiresAt: now() + ttlMs });
    if (map.size > 40) {
        const oldestKey = map.keys().next().value;
        map.delete(oldestKey);
    }
};
const invalidateReviewCaches = () => {
    responseCache.reviews = { value: null, expiresAt: 0 };
    responseCache.comments.clear();
};

const getVectorPrecision = (minLng, minLat, maxLng, maxLat) => {
    const lngSpan = Math.abs(maxLng - minLng);
    const latSpan = Math.abs(maxLat - minLat);
    const span = Math.max(lngSpan, latSpan);

    if (span >= 0.5) return 4;
    return 5;
};

const logBlock = (title, lines) => {
    console.log('');
    console.log(`========== ${title} ==========`);
    for (const line of lines) console.log(line);
    console.log('================================');
};

app.use((req, res, next) => {
    const startedAt = Date.now();
    const ip = formatIp(req);
    const host = shortHost(req);
    res.on('finish', () => {
        const durationMs = Date.now() - startedAt;
        const isReadOnlyGet = req.method === 'GET' && (
            req.originalUrl.startsWith('/api/reviews') ||
            req.originalUrl.startsWith('/api/comments') ||
            req.originalUrl.startsWith('/api/vectors')
        );

        if (isReadOnlyGet && res.statusCode < 400) {
            return;
        }

        console.log(`[HTTP] ${req.method} ${req.originalUrl} -> ${res.statusCode} in ${durationMs}ms | ip=${ip} | host=${host}`);
    });

    next();
});

const pool = new pg.Pool({
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
});

const routeWorkerSettings = resolveRouteWorkerSettings();
const routeWorkerPool = createRouteWorkerPool({
    workerPath: path.resolve(__dirname, 'utils/routeWorker.js'),
    ...routeWorkerSettings,
});

const ensureSchema = async () => {
    await pool.query(`
        CREATE TABLE IF NOT EXISTS review_helpful_votes (
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (review_id, user_id)
        )
    `);
};

const authenticateToken = (req, res, next) => {
    const token = req.headers['authorization']?.split(' ')[1];
    if (!token) return res.status(401).json({ message: 'Не авторизован' });
    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
        if (err) return res.status(403).json({ message: 'Токен истек' });
        req.user = user;
        next();
    });
};

const attachOptionalUser = (req, _res, next) => {
    const token = req.headers['authorization']?.split(' ')[1];
    if (!token) {
        next();
        return;
    }

    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
        if (!err) {
            req.user = user;
        }
        next();
    });
};

// === 1. АККАУНТЫ ===
app.post('/api/register', async (req, res) => {
    try {
        const { username, password } = req.body;
        const exists = await pool.query('SELECT * FROM users WHERE username = $1', [username]);
        if (exists.rows.length > 0) return res.status(400).json({ message: 'Имя занято' });

        const newUser = await pool.query(
            'INSERT INTO users (username, password) VALUES ($1, $2) RETURNING id, username',
            [username, password]
        );

        const token = jwt.sign(newUser.rows[0], process.env.JWT_SECRET, { expiresIn: '24h' });
        logBlock('AUTH REGISTER', [`Status: SUCCESS`, `User: ${newUser.rows[0].username}`]);
        res.json({ token, user: newUser.rows[0] });
    } catch (err) { res.status(500).json({ message: 'Ошибка регистрации' }); }
});

app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        const user = await pool.query('SELECT * FROM users WHERE username = $1', [username]);
        
        if (user.rows.length === 0 || user.rows[0].password !== password) {
            logBlock('AUTH LOGIN', [`Status: FAILED`, `User: ${username}`]);
            return res.status(400).json({ message: 'Неверный логин или пароль' });
        }

        const userData = { id: user.rows[0].id, username: user.rows[0].username };
        const token = jwt.sign(userData, process.env.JWT_SECRET, { expiresIn: '24h' });
        logBlock('AUTH LOGIN', [`Status: SUCCESS`, `User: ${userData.username}`]);
        res.json({ token, user: userData });
    } catch (err) { res.status(500).json({ message: 'Ошибка входа' }); }
});

// === 2. ОТЗЫВЫ ===
app.get('/api/reviews', attachOptionalUser, async (req, res) => {
    try {
        const cacheKey = req.user ? `auth:${req.user.id}` : 'guest';
        const cached = responseCache.reviews.value && responseCache.reviews.expiresAt > now()
            ? responseCache.reviews.value[cacheKey]
            : null;
        if (cached) {
            return res.json(cached);
        }

        const userId = req.user?.id ?? null;
        const result = await pool.query(`
            SELECT
                r.*,
                u.username,
                COALESCE(v.helpful_count, 0) AS helpful_count,
                CASE
                    WHEN $1::int IS NULL THEN false
                    ELSE EXISTS (
                        SELECT 1
                        FROM review_helpful_votes rv
                        WHERE rv.review_id = r.id AND rv.user_id = $1
                    )
                END AS helpful_by_me
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN (
                SELECT review_id, COUNT(*)::int AS helpful_count
                FROM review_helpful_votes
                GROUP BY review_id
            ) v ON v.review_id = r.id
            ORDER BY COALESCE(v.helpful_count, 0) DESC, r.created_at DESC
        `, [userId]);

        const cacheBucket = responseCache.reviews.value && responseCache.reviews.expiresAt > now()
            ? responseCache.reviews.value
            : {};
        cacheBucket[cacheKey] = result.rows;
        cacheSet(responseCache.reviews, cacheBucket, 30000);
        res.json(result.rows);
    } catch (err) { res.status(500).json({ message: 'Ошибка загрузки отзывов' }); }
});

app.post('/api/reviews', authenticateToken, async (req, res) => {
    try {
        const { lat, lng, text, rating } = req.body;
        const newReview = await pool.query(
            'INSERT INTO reviews (user_id, lat, lng, text, rating) VALUES ($1, $2, $3, $4, $5) RETURNING *',
            [req.user.id, lat, lng, text, rating]
        );
        logBlock('REVIEW CREATED', [
            `User: ${formatUser(req)}`,
            `Review ID: ${newReview.rows[0].id}`,
            `Rating: ${rating}`,
            `Point: ${lat}, ${lng}`,
        ]);
        invalidateReviewCaches();
        res.json(newReview.rows[0]);
    } catch (err) { res.status(500).json({ message: 'Ошибка добавления отзыва' }); }
});

app.put('/api/reviews/:id', authenticateToken, async (req, res) => {
    try {
        const { text, rating } = req.body;
        const updatedReview = await pool.query(
            'UPDATE reviews SET text = $1, rating = $2 WHERE id = $3 AND user_id = $4 RETURNING *',
            [text, rating, req.params.id, req.user.id]
        );
        if (updatedReview.rows.length === 0) {
            return res.status(403).json({ message: 'У вас нет прав на изменение этого отзыва' });
        }

        logBlock('REVIEW UPDATED', [
            `User: ${formatUser(req)}`,
            `Review ID: ${req.params.id}`,
            `Rating: ${rating}`,
        ]);
        invalidateReviewCaches();
        res.json(updatedReview.rows[0]);
    } catch (err) {
        res.status(500).json({ message: 'Ошибка изменения отзыва' });
    }
});

app.delete('/api/reviews/:id', authenticateToken, async (req, res) => {
    try {
        await pool.query('DELETE FROM reviews WHERE id = $1 AND user_id = $2', [req.params.id, req.user.id]);
        logBlock('REVIEW DELETED', [`User: ${formatUser(req)}`, `Review ID: ${req.params.id}`]);
        invalidateReviewCaches();
        res.json({ success: true });
    } catch (err) { res.status(500).json({ message: 'Ошибка удаления отзыва' }); }
});

app.post('/api/reviews/:id/helpful', authenticateToken, async (req, res) => {
    try {
        const existing = await pool.query(
            'SELECT 1 FROM review_helpful_votes WHERE review_id = $1 AND user_id = $2',
            [req.params.id, req.user.id]
        );

        let helpfulByMe = false;
        if (existing.rows.length > 0) {
            await pool.query(
                'DELETE FROM review_helpful_votes WHERE review_id = $1 AND user_id = $2',
                [req.params.id, req.user.id]
            );
        } else {
            await pool.query(
                'INSERT INTO review_helpful_votes (review_id, user_id) VALUES ($1, $2)',
                [req.params.id, req.user.id]
            );
            helpfulByMe = true;
        }

        const countResult = await pool.query(
            'SELECT COUNT(*)::int AS helpful_count FROM review_helpful_votes WHERE review_id = $1',
            [req.params.id]
        );

        logBlock('REVIEW HELPFUL', [
            `User: ${formatUser(req)}`,
            `Review ID: ${req.params.id}`,
            `Action: ${helpfulByMe ? 'SET' : 'UNSET'}`,
            `Count: ${countResult.rows[0].helpful_count}`,
        ]);
        invalidateReviewCaches();
        res.json({
            success: true,
            helpfulCount: countResult.rows[0].helpful_count,
            helpfulByMe,
        });
    } catch (err) {
        res.status(500).json({ message: 'Ошибка обновления полезности' });
    }
});

// === 3. КОММЕНТАРИИ ===
app.get('/api/comments/:review_id', async (req, res) => {
    try {
        const cacheKey = String(req.params.review_id);
        const cached = cacheMapGet(responseCache.comments, cacheKey);
        if (cached) {
            return res.json(cached);
        }

        const result = await pool.query(`
            SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id = u.id 
            WHERE c.review_id = $1 ORDER BY c.created_at ASC
        `, [req.params.review_id]);
        cacheMapSet(responseCache.comments, cacheKey, result.rows, 30000);
        res.json(result.rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: 'Ошибка загрузки комментариев' });
    }
});

app.post('/api/comments/:review_id', authenticateToken, async (req, res) => {
    try {
        const newComment = await pool.query(
            'INSERT INTO comments (review_id, user_id, text) VALUES ($1, $2, $3) RETURNING *',
            [req.params.review_id, req.user.id, req.body.text]
        );
        logBlock('COMMENT CREATED', [
            `User: ${formatUser(req)}`,
            `Comment ID: ${newComment.rows[0].id}`,
            `Review ID: ${req.params.review_id}`,
        ]);
        responseCache.comments.delete(String(req.params.review_id));
        res.json(newComment.rows[0]);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: 'Ошибка добавления комментария' });
    }
});

// ИЗМЕНИТЬ КОММЕНТАРИЙ
app.put('/api/comments/:id', authenticateToken, async (req, res) => {
    try {
        const { text } = req.body;
        const result = await pool.query(
            'UPDATE comments SET text = $1 WHERE id = $2 AND user_id = $3 RETURNING *',
            [text, req.params.id, req.user.id]
        );
        if (result.rows.length === 0) return res.status(403).json({ message: 'У вас нет прав на изменение этого комментария' });
        logBlock('COMMENT UPDATED', [`User: ${formatUser(req)}`, `Comment ID: ${req.params.id}`]);
        responseCache.comments.clear();
        res.json(result.rows[0]);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: 'Ошибка изменения комментария' });
    }
});

// УДАЛИТЬ КОММЕНТАРИЙ
app.delete('/api/comments/:id', authenticateToken, async (req, res) => {
    try {
        const result = await pool.query('DELETE FROM comments WHERE id = $1 AND user_id = $2 RETURNING *', [req.params.id, req.user.id]);
        if (result.rows.length === 0) return res.status(403).json({ message: 'У вас нет прав на удаление этого комментария' });
        logBlock('COMMENT DELETED', [`User: ${formatUser(req)}`, `Comment ID: ${req.params.id}`]);
        responseCache.comments.clear();
        res.json({ success: true });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: 'Ошибка удаления комментария' });
    }
});

// === 4. ОПТИМИЗИРОВАННАЯ ЗАГРУЗКА ВЕКТОРОВ ===
app.get('/api/vectors', async (req, res) => {
    try {
        const { bbox } = req.query; 
        if (!bbox) return res.json({ water: [], roads: [] });

        const cached = cacheMapGet(responseCache.vectors, bbox);
        if (cached) {
            return res.json(cached);
        }

        const [minLng, minLat, maxLng, maxLat] = bbox.split(',').map(Number);
        const precision = getVectorPrecision(minLng, minLat, maxLng, maxLat);
        const params = [minLng, minLat, maxLng, maxLat, precision];

        const waterQuery = await pool.query(`
            SELECT ST_AsGeoJSON(
                geom,
                $5
            ) as geojson
            FROM water_poly
            WHERE geom IS NOT NULL
              AND geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
              AND ST_Intersects(geom, ST_MakeEnvelope($1, $2, $3, $4, 4326))
        `, params);
        
        const roadsQuery = await pool.query(`
            SELECT ST_AsGeoJSON(
                geom,
                $5
            ) as geojson
            FROM roads_lines
            WHERE geom IS NOT NULL
              AND geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
              AND ST_Intersects(geom, ST_MakeEnvelope($1, $2, $3, $4, 4326))
        `, params);

        const payload = {
            water: waterQuery.rows.map(r => JSON.parse(r.geojson)),
            roads: roadsQuery.rows.map(r => JSON.parse(r.geojson))
        };

        cacheMapSet(responseCache.vectors, bbox, payload, 20000);
        res.json(payload);
    } catch (err) {
        console.error("Ошибка загрузки векторов:", err);
        res.status(500).json({ error: 'Ошибка БД при загрузке векторов' });
    }
});

// === 5. МАРШРУТИЗАЦИЯ A* НА СЕРВЕРЕ ===
app.post('/api/route', async (req, res) => {
    try {
        const { startCoord, endCoord, weights } = req.body;
        logBlock('ROUTE REQUEST', [
            `Start: ${startCoord?.join?.(',') || 'n/a'}`,
            `End: ${endCoord?.join?.(',') || 'n/a'}`,
            `Field weight: ${weights?.field ?? 'n/a'}`,
            `Slope penalty: ${weights?.slope ?? 'n/a'}`,
        ]);
        const result = await routeWorkerPool.runRoute(startCoord, endCoord, weights);
        
        if (result?.success && result.path) {
            logBlock('ROUTE SUCCESS', [
                `Points: ${result.path.length}`,
                `Length: ${result.stats?.lengthKm ?? 'n/a'} km`,
                `Gain: ${result.stats?.gain ?? 'n/a'} m`,
                `Loss: ${result.stats?.loss ?? 'n/a'} m`,
            ]);
            res.json({ success: true, path: result.path, stats: result.stats });
        } else {
            logBlock('ROUTE RESULT', [
                `Status: NOT FOUND`,
                `Reason: ${result?.reason ?? 'unknown'}`,
                `Message: ${result?.message ?? 'Путь не найден'}`,
            ]);
            res.status(400).json({
                success: false,
                reason: result?.reason ?? 'no_path',
                message: result?.message ?? 'Путь не найден',
                details: result?.details ?? null,
            });
        }
    } catch (err) {
        if (err instanceof RouteQueueFullError) {
            res.status(503).json({
                success: false,
                reason: 'route_queue_full',
                message: 'Сервер занят расчетом маршрутов. Повторите запрос позже.',
                details: routeWorkerPool.stats(),
            });
            return;
        }

        if (err instanceof RouteTaskTimeoutError) {
            res.status(504).json({
                success: false,
                reason: 'route_timeout',
                message: 'Расчет маршрута занял слишком много времени. Попробуйте выбрать точки ближе друг к другу.',
                details: routeWorkerPool.stats(),
            });
            return;
        }

        console.error(err);
        res.status(500).json({ success: false, message: 'Ошибка сервера при расчете маршрута' });
    }
});

const PORT = process.env.PORT || 5000;

const shutdown = async (signal) => {
    logBlock('SERVER SHUTDOWN', [`Signal: ${signal}`]);
    try {
        await routeWorkerPool.shutdown();
        await pool.end();
    } catch (err) {
        console.error('Ошибка остановки сервера:', err);
    } finally {
        process.exit(0);
    }
};

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));

ensureSchema()
    .then(() => {
        app.listen(PORT, () => {
            logBlock('SERVER READY', [
                `URL: http://localhost:${PORT}`,
                `Route workers: ${routeWorkerSettings.size}`,
                `Route queue max: ${routeWorkerSettings.maxQueue}`,
                `Route timeout: ${routeWorkerSettings.taskTimeoutMs}ms`,
            ]);
        });
    })
    .catch((err) => {
        console.error('Не удалось подготовить схему БД:', err);
        process.exit(1);
    });
