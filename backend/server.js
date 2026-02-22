const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const YahooFinance = require('yahoo-finance2').default;
const yahooFinance = new YahooFinance();
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

const dbPath = path.join(__dirname, '..', 'portfolio.db');

// Inicializar base de datos
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error al abrir la base de datos', err.message);
    } else {
        // Asegurar tabla
        db.run(`CREATE TABLE IF NOT EXISTS portfolio (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      company TEXT NOT NULL,
      quantity REAL NOT NULL,
      buy_price REAL NOT NULL,
      buy_date TEXT NOT NULL,
      current_price REAL DEFAULT 0,
      status TEXT DEFAULT 'OPEN',
      sell_price REAL,
      sell_date TEXT
    )`);
    }
});

// GET /api/portfolio - Obtener cartera y actualizar precios
app.get('/api/portfolio', async (req, res) => {
    db.all("SELECT * FROM portfolio WHERE status = 'OPEN'", async (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }

        let totalInvested = 0;
        let totalValue = 0;
        let totalGain = 0;

        const data = await Promise.all(rows.map(async (row) => {
            let currentPrice = row.current_price || 0;
            try {
                const quote = await yahooFinance.quote(row.symbol);
                if (quote && quote.regularMarketPrice) {
                    currentPrice = quote.regularMarketPrice;
                    // Actualizamos la DB asíncronamente en segundo plano
                    db.run('UPDATE portfolio SET current_price = ? WHERE id = ?', [currentPrice, row.id]);
                }
            } catch (e) {
                console.error(`Error en Yahoo Finance para ${row.symbol}:`, e.message);
            }

            const total_invested = row.quantity * row.buy_price;
            const current_total = row.quantity * currentPrice;
            const gain = current_total - total_invested;

            totalInvested += total_invested;
            totalValue += current_total;
            totalGain += gain;

            // Adaptar el formato de salida para que coincida con el frontend hecho anteriormente
            return {
                id: row.id,
                Symbol: row.symbol,
                Company: row.company,
                Quantity: row.quantity,
                BuyPrice: row.buy_price,
                BuyDate: row.buy_date,
                CurrentPrice: currentPrice,
                TotalInvested: total_invested,
                CurrentTotal: current_total,
                Gain: gain
            };
        }));

        res.json({
            data: data,
            summary: {
                total_invested: totalInvested,
                total_value: totalValue,
                total_gain: totalGain
            }
        });
    });
});

// GET /api/quote/:symbol - Obtener nombre de la empresa y precio al instante
app.get('/api/quote/:symbol', async (req, res) => {
    const symbol = req.params.symbol.trim().toUpperCase();
    try {
        const quote = await yahooFinance.quote(symbol);
        if (quote) {
            return res.json({
                symbol: symbol,
                company: quote.shortName || quote.longName || symbol,
                price: quote.regularMarketPrice || 0
            });
        } else {
            return res.status(404).json({ error: 'Símbolo no encontrado' });
        }
    } catch (e) {
        console.error(`Error obteniendo quote para ${symbol}:`, e.message);
        return res.status(500).json({ error: 'Error interno obteniendo cotización' });
    }
});

// POST /api/portfolio - Añadir nueva compra
app.post('/api/portfolio', async (req, res) => {
    const { symbol, quantity, buy_price, buy_date: user_buy_date, company: user_company } = req.body;
    if (!symbol || !quantity || buy_price === undefined) {
        return res.status(400).json({ error: 'Faltan datos obligatorios (symbol, quantity, buy_price)' });
    }

    const cleanSymbol = symbol.trim().toUpperCase();
    let company = user_company || cleanSymbol;
    let current_price = 0;

    try {
        const quote = await yahooFinance.quote(cleanSymbol);
        if (quote) {
            if (!user_company) company = quote.shortName || quote.longName || cleanSymbol;
            current_price = quote.regularMarketPrice || 0;
        }
    } catch (e) {
        console.warn(`No se pudo obtener nombre de compañía en Yahoo Finance para ${cleanSymbol}`);
    }

    // Si el usuario provee una fecha la usamos, de lo contrario usamos hoy
    const buy_date = user_buy_date || new Date().toISOString().split('T')[0];

    db.run(
        'INSERT INTO portfolio (symbol, company, quantity, buy_price, buy_date, current_price) VALUES (?, ?, ?, ?, ?, ?)',
        [cleanSymbol, company, quantity, buy_price, buy_date, current_price],
        function (err) {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            res.json({ message: 'Posición añadida', id: this.lastID });
        }
    );
});

// PUT /api/portfolio/:id - Modificar compra existente
app.put('/api/portfolio/:id', async (req, res) => {
    const id = req.params.id;
    const { symbol, quantity, buy_price, buy_date: user_buy_date, company: user_company } = req.body;

    if (!symbol || !quantity || buy_price === undefined) {
        return res.status(400).json({ error: 'Faltan datos obligatorios (symbol, quantity, buy_price)' });
    }

    const cleanSymbol = symbol.trim().toUpperCase();
    let company = user_company || cleanSymbol;
    let current_price = 0;

    // Obtener precio actual (y empresa si el usuario no la ingresó)
    try {
        const quote = await yahooFinance.quote(cleanSymbol);
        if (quote) {
            if (!user_company || user_company === cleanSymbol) {
                company = quote.shortName || quote.longName || cleanSymbol;
            }
            current_price = quote.regularMarketPrice || 0;
        }
    } catch (e) {
        console.warn(`No se pudo obtener nombre de compañía en Yahoo Finance para modificar ${cleanSymbol}`);
    }

    const buy_date = user_buy_date || new Date().toISOString().split('T')[0];

    db.run(
        'UPDATE portfolio SET symbol = ?, company = ?, quantity = ?, buy_price = ?, buy_date = ?, current_price = ? WHERE id = ?',
        [cleanSymbol, company, quantity, buy_price, buy_date, current_price, id],
        function (err) {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            if (this.changes === 0) {
                return res.status(404).json({ error: 'Posición no encontrada' });
            }
            res.json({ message: 'Posición actualizada correctamente', changes: this.changes });
        }
    );
});

// DELETE /api/portfolio/:id - Eliminar posición por error
app.delete('/api/portfolio/:id', (req, res) => {
    const id = req.params.id;
    db.run('DELETE FROM portfolio WHERE id = ?', [id], function (err) {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({ message: 'Posición eliminada', changes: this.changes });
    });
});

// POST /api/portfolio/:id/sell - Vender posición
app.post('/api/portfolio/:id/sell', (req, res) => {
    const id = req.params.id;
    const { sell_price, sell_date } = req.body;

    if (sell_price === undefined || !sell_date) {
        return res.status(400).json({ error: 'Faltan datos de venta (sell_price, sell_date)' });
    }

    db.run(
        "UPDATE portfolio SET status = 'CLOSED', sell_price = ?, sell_date = ? WHERE id = ?",
        [sell_price, sell_date, id],
        function (err) {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            res.json({ message: 'Posición vendida exitosamente', changes: this.changes });
        }
    );
});

// Healthcheck
app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', server: 'node' });
});

// Función auxiliar para leer caché
function readCache(cachePath, res, errorMsg) {
    const fs = require('fs');
    fs.readFile(cachePath, 'utf8', (err, data) => {
        if (err) {
            console.error(errorMsg, err);
            return res.status(500).json({ error: errorMsg });
        }
        try {
            const cache = JSON.parse(data);
            if (cache.rate) {
                return res.json({ price: cache.rate, last_updated: cache.timestamp, cached: true });
            }
        } catch (parseErr) {
            console.error('Error parsing cache', parseErr);
        }
        res.status(500).json({ error: errorMsg });
    });
}

// GET /api/exchange-rate - Obtener cotización Dólar Cripto (USDT/ARS) de Binance
app.get('/api/exchange-rate', async (req, res) => {
    const fs = require('fs');
    const cachePath = path.join(__dirname, '..', 'rate_cache.json');

    try {
        // Obtenemos dinámicamente el módulo nativo "https"
        const https = require('https');
        https.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTARS', (resp) => {
            let data = '';
            resp.on('data', (chunk) => { data += chunk; });
            resp.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    if (parsed.price) {
                        const price = parseFloat(parsed.price);
                        const last_updated = new Date().toISOString();

                        // Guardar en caché
                        const cacheData = { rate: price, source: 'USDT (Binance)', timestamp: last_updated };
                        fs.writeFile(cachePath, JSON.stringify(cacheData), (err) => {
                            if (err) console.error('Error guardando rate_cache.json:', err);
                        });

                        res.json({ price: price, last_updated: last_updated });
                    } else {
                        readCache(cachePath, res, 'No se encontró precio para USDTARS y caché no disponible');
                    }
                } catch (err) {
                    readCache(cachePath, res, 'Error analizando respuesta de Binance');
                }
            });
        }).on("error", (err) => {
            readCache(cachePath, res, err.message);
        });
    } catch (e) {
        readCache(cachePath, res, 'Fallo al interconectar con Binance');
    }
});

const PORT = 8000;
// Escuchar explícitamente en localhost para seguridad y estabilidad
app.listen(PORT, '127.0.0.1', () => {
    console.log('==================================================');
    console.log(`Portafolio Zen Backend - Creado por Fabian A.Correa`);
    console.log('==================================================');
    console.log(`Servidor Node.js corriendo en http://127.0.0.1:${PORT}`);
    console.log('==================================================');
});
