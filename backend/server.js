const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const yahooFinance = require('yahoo-finance2').default;
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
      current_price REAL DEFAULT 0
    )`);
    }
});

// GET /api/portfolio - Obtener cartera y actualizar precios
app.get('/api/portfolio', async (req, res) => {
    db.all('SELECT * FROM portfolio', async (err, rows) => {
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

// POST /api/portfolio - Añadir nueva compra
app.post('/api/portfolio', async (req, res) => {
    const { symbol, quantity, buy_price } = req.body;
    if (!symbol || !quantity || buy_price === undefined) {
        return res.status(400).json({ error: 'Faltan datos obligatorios (symbol, quantity, buy_price)' });
    }

    const cleanSymbol = symbol.trim().toUpperCase();
    let company = cleanSymbol;
    let current_price = 0;

    try {
        const quote = await yahooFinance.quote(cleanSymbol);
        if (quote) {
            company = quote.shortName || quote.longName || cleanSymbol;
            current_price = quote.regularMarketPrice || 0;
        }
    } catch (e) {
        console.warn(`No se pudo obtener nombre de compañía en Yahoo Finance para ${cleanSymbol}`);
    }

    // Fecha de hoy (YYYY-MM-DD)
    const buy_date = new Date().toISOString().split('T')[0];

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

// DELETE /api/portfolio/:id - Vender/Eliminar posición
app.delete('/api/portfolio/:id', (req, res) => {
    const id = req.params.id;
    db.run('DELETE FROM portfolio WHERE id = ?', [id], function (err) {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({ message: 'Posición eliminada', changes: this.changes });
    });
});

// Healthcheck
app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', server: 'node' });
});

const PORT = 8000;
// Escuchar explícitamente en localhost para seguridad y estabilidad
app.listen(PORT, '127.0.0.1', () => {
    console.log(`Servidor Node.js corriendo en http://127.0.0.1:${PORT}`);
});
