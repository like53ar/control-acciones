const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const YahooFinance = require('yahoo-finance2').default;
const yahooFinance = new YahooFinance();
const path = require('path');
const { translate } = require('@vitalets/google-translate-api');

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

        db.run(`CREATE TABLE IF NOT EXISTS historical_prices (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date TEXT NOT NULL,
      time TEXT NOT NULL,
      symbol TEXT NOT NULL,
      price REAL NOT NULL
    )`);
    }
});

// GET /api/portfolio - Obtener cartera y actualizar precios
app.get('/api/portfolio', async (req, res) => {
    // 1. Obtener posiciones abiertas
    db.all("SELECT * FROM portfolio WHERE status = 'OPEN'", async (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });

        let totalInvested = 0;
        let totalValue = 0;
        let totalGain = 0;

        const data = await Promise.all(rows.map(async (row) => {
            let currentPrice = row.current_price || 0;
            try {
                const quote = await yahooFinance.quote(row.symbol);
                if (quote && quote.regularMarketPrice) {
                    currentPrice = quote.regularMarketPrice;
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

        // 2. Calcular Ganancias Realizadas (de posiciones CLOSED)
        db.get("SELECT SUM((sell_price - buy_price) * quantity) as realizedGain FROM portfolio WHERE status = 'CLOSED'", (err, result) => {
            const totalRealizedGain = (result && result.realizedGain) ? result.realizedGain : 0;

            res.json({
                data: data,
                summary: {
                    total_invested: totalInvested,
                    total_value: totalValue,
                    total_gain: totalGain,
                    total_realized_gain: totalRealizedGain
                }
            });
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

// GET /api/radar - Devuelve radar de mercado en vivo
app.get('/api/radar', async (req, res) => {
    try {
        const symbols = ['^GSPC', '^IXIC', '^DJI', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'TSLA', 'GC=F', 'CL=F', 'BTC-USD', 'EURUSD=X'];
        const results = await yahooFinance.quote(symbols);
        const radar = results.map(q => ({
            symbol: q.symbol,
            name: q.shortName || q.longName || q.symbol,
            price: q.regularMarketPrice,
            changePct: q.regularMarketChangePercent
        }));
        res.json(radar);
    } catch (error) {
        console.error('Error al obtener datos de radar:', error);
        res.status(500).json({ error: 'Error al obtener radar' });
    }
});

// GET /api/news/:category - Devuelve noticias relevantes
app.get('/api/news/:category', async (req, res) => {
    try {
        const category = req.params.category;
        let query = 'SPY';
        if (category === 'macro') query = 'SPY';
        if (category === 'empresas') query = 'QQQ';
        if (category === 'cripto') query = 'BTC-USD';

        const result = await yahooFinance.search(query, { newsCount: 15, quotesCount: 0 });
        const news = await Promise.all(result.news.map(async (n) => {
            let titleEs = n.title;
            try {
                const trUrl = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q=${encodeURIComponent(n.title)}`;
                const trRes = await fetch(trUrl);
                const trJson = await trRes.json();
                if (trJson && trJson[0]) {
                    titleEs = trJson[0].map(item => item[0]).join('');
                }
            } catch (e) {
                console.error("Error al traducir:", e.message);
            }
            return {
                title: titleEs,
                link: n.link,
                publisher: n.publisher || 'Yahoo Finance',
                timestamp: n.providerPublishTime,
                uuid: n.uuid
            };
        }));
        res.json(news);
    } catch (error) {
        console.error('Error al obtener noticias:', error);
        res.status(500).json({ error: 'Error al obtener noticias' });
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

// POST /api/portfolio/:id/sell - Vender posición (soporta ventas parciales)
app.post('/api/portfolio/:id/sell', (req, res) => {
    const id = req.params.id;
    const { sell_price, sell_date, quantity: sell_quantity } = req.body;

    if (sell_price === undefined || !sell_date || !sell_quantity) {
        return res.status(400).json({ error: 'Faltan datos de venta (sell_price, sell_date, quantity)' });
    }

    // 1. Obtener la posición actual
    db.get("SELECT * FROM portfolio WHERE id = ?", [id], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });
        if (!row) return res.status(404).json({ error: 'Posición no encontrada' });
        if (row.status === 'CLOSED') return res.status(400).json({ error: 'La posición ya está cerrada' });

        const currentQuantity = row.quantity;
        const sellQty = parseFloat(sell_quantity);

        if (sellQty > currentQuantity) {
            return res.status(400).json({ error: 'No puedes vender más de lo que posees' });
        }

        if (sellQty < currentQuantity) {
            // VENTA PARCIAL
            const remainingQty = currentQuantity - sellQty;

            db.serialize(() => {
                // A. Actualizar posición original con la cantidad restante
                db.run("UPDATE portfolio SET quantity = ? WHERE id = ?", [remainingQty, id]);

                // B. Insertar nueva posición cerrada con la cantidad vendida
                db.run(
                    "INSERT INTO portfolio (symbol, company, quantity, buy_price, buy_date, current_price, status, sell_price, sell_date) VALUES (?, ?, ?, ?, ?, ?, 'CLOSED', ?, ?)",
                    [row.symbol, row.company, sellQty, row.buy_price, row.buy_date, row.current_price, sell_price, sell_date],
                    function (err) {
                        if (err) return res.status(500).json({ error: err.message });
                        res.json({ message: 'Venta parcial realizada con éxito', id: this.lastID, partial: true });
                    }
                );
            });
        } else {
            // VENTA TOTAL (Igual que antes pero mantenemos consistencia)
            db.run(
                "UPDATE portfolio SET status = 'CLOSED', sell_price = ?, sell_date = ? WHERE id = ?",
                [sell_price, sell_date, id],
                function (err) {
                    if (err) return res.status(500).json({ error: err.message });
                    res.json({ message: 'Posición vendida exitosamente (Venta Total)', changes: this.changes });
                }
            );
        }
    });
});


// Healthcheck
app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', server: 'node' });
});

// GET /api/historical-prices
app.get('/api/historical-prices', (req, res) => {
    db.all('SELECT * FROM historical_prices ORDER BY symbol ASC, date ASC, time ASC', (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ data: rows });
    });
});

// POST /api/historical-prices
app.post('/api/historical-prices', (req, res) => {
    const { date, time, assets } = req.body;
    if (!date || !time || !assets || !assets.length) {
        return res.status(400).json({ error: 'Faltan datos (date, time, assets)' });
    }

    db.serialize(() => {
        // Eliminar registros anteriores del mismo día para mantener sólo el último snapshot
        db.run('DELETE FROM historical_prices WHERE date = ?', [date], (err) => {
            if (err) return res.status(500).json({ error: err.message });

            const stmt = db.prepare('INSERT INTO historical_prices (date, time, symbol, price) VALUES (?, ?, ?, ?)');
            assets.forEach(asset => {
                stmt.run([date, time, asset.symbol, asset.price]);
            });
            stmt.finalize((err) => {
                if (err) return res.status(500).json({ error: err.message });
                res.json({ message: 'Precios históricos guardados exitosamente' });
            });
        });
    });
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

// POST /api/shutdown - Cierra la aplicación matando los procesos de Node
app.post('/api/shutdown', (req, res) => {
    res.json({ message: 'Apagando el sistema...' });
    const { exec } = require('child_process');
    console.log('Cierre del sistema solicitado por el usuario.');
    // Esperar unos ms para que la respuesta llegue al cliente
    setTimeout(() => {
        exec('taskkill /F /IM node.exe /T', (err, stdout, stderr) => {
            if (err) {
                console.error('Error al intentar cerrar node.exe:', err);
            }
        });
    }, 1000);
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
