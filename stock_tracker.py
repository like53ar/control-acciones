import customtkinter as ctk
import pandas as pd
import yfinance as yf
import os
import threading
import queue
from tkinter import messagebox
import requests
import sqlite3
from datetime import datetime
import time
import random
import shutil
from tkinter import filedialog


import logging
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
import config

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_tracker.log"),
        logging.StreamHandler()
    ]
)

DB_FILE = config.DB_FILE
CSV_FILE = config.CSV_FILE

class DBWorker:
    def __init__(self) -> None:

        self.queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        # Dedicated connection for the writer thread
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        while self.running:
            try:
                task = self.queue.get()
                if task is None:
                    break
                
                func, args, callback = task
                try:
                    # Execute the DB operation
                    # We pass the cursor to the function so it executes on this connection
                    res = func(cursor, *args)
                    conn.commit()
                    
                    # If there's a callback, run it (usually UI update)
                    if callback:
                        callback(res)
                except Exception as e:
                    logging.error(f"DB Worker Error: {e}")
                    conn.rollback()
                finally:
                    self.queue.task_done()
            except Exception as e:
                logging.error(f"Worker Loop Error: {e}")
        
        conn.close()

    def submit(self, func, args=(), callback=None):
        self.queue.put((func, args, callback))

    def stop(self):
        self.queue.put(None)

# Global Worker Instance
db_worker = DBWorker()

class PortfolioDB:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                company TEXT,
                action TEXT, -- 'BUY', 'SELL'
                quantity REAL,
                price REAL
            )
        ''')
        
        # Portfolio Table - Now with Individual Lots support
        # We need a unique ID for each lot. Symbol is no longer unique/PK.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company TEXT,
                quantity REAL,
                buy_price REAL,
                buy_date TEXT,
                current_price REAL DEFAULT 0
            )
        ''')
        
        # Check if column exists (old schema migration)
        # This block is now mostly for handling transitions from older schemas.
        # If 'buy_date' is missing, it implies an older schema that needs rebuilding.
        # The main app init will handle the rebuild.
        try:
            cursor.execute('ALTER TABLE portfolio ADD COLUMN current_price REAL DEFAULT 0')
        except sqlite3.OperationalError:
            pass # Column already exists or other error, ignore for now.

        # Indexes for Performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')

        # Price History table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                date TEXT,
                price REAL,
                UNIQUE(symbol, date)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_symbol ON price_history(symbol)')
        
        # Add transaction_id to portfolio if not exists (Persistent Deletion support)
        try:
             cursor.execute('ALTER TABLE portfolio ADD COLUMN transaction_id INTEGER')
        except sqlite3.OperationalError:
             pass

        conn.commit()
        conn.close()

    @staticmethod
    def rebuild_portfolio_from_transactions():
        """Rebuilds the portfolio table from scratch using transactions (FIFO logic for sells)"""
        logging.info("Rebuilding portfolio from transactions...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # Clear current portfolio
            cursor.execute("DELETE FROM portfolio")
            
            # Get all transactions sorted by date/id
            cursor.execute("SELECT id, symbol, company, action, quantity, price, date FROM transactions ORDER BY date ASC, id ASC")
            transactions = cursor.fetchall()
            
            # Track lots in memory: symbol -> list of {qty, price, date, company, txn_id}
            portfolio_lots = {}
            
            for txn_id, symbol, company, action, quantity, price, date in transactions:
                if symbol not in portfolio_lots:
                    portfolio_lots[symbol] = []
                
                if action == 'BUY':
                    portfolio_lots[symbol].append({
                        'qty': quantity, 
                        'price': price, 
                        'date': date,
                        'company': company,
                        'txn_id': txn_id
                    })
                elif action == 'SELL':
                    qty_to_sell = quantity
                    # FIFO Strategy
                    while qty_to_sell > 0 and portfolio_lots[symbol]:
                        lot = portfolio_lots[symbol][0]
                        if lot['qty'] > qty_to_sell:
                            lot['qty'] -= qty_to_sell
                            qty_to_sell = 0
                        else:
                            qty_to_sell -= lot['qty']
                            portfolio_lots[symbol].pop(0)
            
            # Insert remaining lots back into DB
            for symbol, lots in portfolio_lots.items():
                for lot in lots:
                    cursor.execute('''
                        INSERT INTO portfolio (symbol, company, quantity, buy_price, buy_date, current_price, transaction_id)
                        VALUES (?, ?, ?, ?, ?, 0, ?)
                    ''', (symbol, lot['company'], lot['qty'], lot['price'], lot['date'], lot['txn_id']))
            
            conn.commit()
            logging.info("Portfolio rebuild complete.")
        except Exception as e:
            logging.error(f"Rebuild failed: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def backup_db() -> None:
        """Create a daily backup of the database"""
        if not os.path.exists(DB_FILE):
            return
            
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        backup_file = os.path.join(backup_dir, f"portfolio_{date_str}.db.bak")
        
        try:
            if not os.path.exists(backup_file):
                shutil.copy2(DB_FILE, backup_file)
                logging.info(f"Database backup created: {backup_file}")
                
                # Prune old backups (keep last 7 days)
                backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".db.bak")])
                while len(backups) > 7:
                    os.remove(backups[0])
                    logging.info(f"Removed old backup: {backups[0]}")
                    backups.pop(0)
        except Exception as e:
            logging.error(f"Backup failed: {e}")

    @staticmethod
    def migrate_csv_if_needed() -> None:
        if os.path.exists(CSV_FILE) and not os.path.exists(DB_FILE):
            logging.info("Migrating CSV to DB...")
            PortfolioDB.init_db()
            try:
                # Use on_bad_lines='skip' to avoid crashing on malformed lines
                df = pd.read_csv(CSV_FILE, on_bad_lines='skip')
                
                # Check for required columns
                required_cols = ['Symbol', 'Quantity', 'BuyPrice']
                if not all(col in df.columns for col in required_cols):
                    logging.error("CSV missing required columns for migration")
                    return

                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                current_date = datetime.now().strftime("%d/%m/%Y")
                
                for _, row in df.iterrows():
                    symbol = str(row['Symbol']).strip().upper()
                    if not symbol: continue
                    
                    qty = float(row['Quantity'])
                    price = float(row['BuyPrice'])
                    # company might be missing or named differently
                    company = str(row.get('Company', symbol))
                    buy_date = str(row.get('BuyDate', current_date))
                    
                    # Direct insert to avoid threading issues during startup
                    # 1. Log transaction
                    cursor.execute('''
                        INSERT INTO transactions (date, symbol, company, action, quantity, price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (buy_date, symbol, company, 'BUY', qty, price))
                    
                    # 2. Insert into portfolio as individual lot
                    cursor.execute('''
                        INSERT INTO portfolio (symbol, company, quantity, buy_price, buy_date, current_price)
                        VALUES (?, ?, ?, ?, ?, 0)
                    ''', (symbol, company, qty, price, buy_date))
                
                conn.commit()
                conn.close()
                
                # Rename CSV to avoid re-migration
                shutil.move(CSV_FILE, f"{CSV_FILE}.migrated")
                logging.info("Migration completed successfully")
                
            except Exception as e:
                logging.error(f"Migration failed: {e}")
                # If migration partially failed, we might want to delete the partial DB so it tries again?
                # For now let's just log.
        elif not os.path.exists(DB_FILE):
             PortfolioDB.init_db()

    # --- Write Operations (Queued) ---

    @staticmethod
    def _execute_sql(cursor, sql, params=()):
        """Generic helper to execute SQL with parameters."""
        cursor.execute(sql, params)

    @staticmethod
    def _add_transaction_sql(cursor, symbol, company, action, quantity, price, date):
        # 1. Log transaction
        cursor.execute('''
            INSERT INTO transactions (date, symbol, company, action, quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, symbol, company, action, quantity, price))
        
        txn_id = cursor.lastrowid
        
        # 2. Update Portfolio State (Individual Lots)
        if action == 'BUY':
            # Just add a new row
            cursor.execute('''
                INSERT INTO portfolio (symbol, company, quantity, buy_price, buy_date, current_price, transaction_id)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (symbol, company, quantity, price, date, txn_id))
            
        elif action == 'SELL':
            # FIFO Logic: Deduct from oldest lots first
            qty_to_sell = quantity
            
            # Get lots sorted by date (and id/insertion order implicitly)
            cursor.execute("SELECT id, quantity FROM portfolio WHERE symbol = ? ORDER BY buy_date ASC, id ASC", (symbol,))
            lots = cursor.fetchall()
            
            for lot_id, lot_qty in lots:
                if qty_to_sell <= 0:
                    break
                    
                if lot_qty > qty_to_sell:
                    # Partial sell of this lot
                    new_qty = lot_qty - qty_to_sell
                    cursor.execute("UPDATE portfolio SET quantity = ? WHERE id = ?", (new_qty, lot_id))
                    qty_to_sell = 0
                else:
                    # Full sell of this lot
                    cursor.execute("DELETE FROM portfolio WHERE id = ?", (lot_id,))
                    qty_to_sell -= lot_qty

    @staticmethod
    def add_transaction(symbol, company, action, quantity, price, date, callback=None):
        db_worker.submit(PortfolioDB._add_transaction_sql, (symbol, company, action, quantity, price, date), callback)

    @staticmethod
    def _update_position_by_id_sql(cursor, pos_id, quantity, buy_price, buy_date):
        cursor.execute('UPDATE portfolio SET quantity = ?, buy_price = ?, buy_date = ? WHERE id = ?', 
                       (quantity, buy_price, buy_date, pos_id))

    @staticmethod
    def update_position_by_id(pos_id, quantity, buy_price, buy_date, callback=None):
        db_worker.submit(PortfolioDB._update_position_by_id_sql, (pos_id, quantity, buy_price, buy_date), callback)

    @staticmethod
    def delete_symbol(symbol, callback=None):
         db_worker.submit(PortfolioDB._execute_sql, ('DELETE FROM portfolio WHERE symbol = ?', (symbol,)), callback)
    
    @staticmethod
    def _delete_position_by_id_sql(cursor, pos_id):
        # Find transaction ID from portfolio
        cursor.execute("SELECT transaction_id FROM portfolio WHERE id = ?", (pos_id,))
        row = cursor.fetchone()
        
        # Delete from Portfolio
        cursor.execute('DELETE FROM portfolio WHERE id = ?', (pos_id,))
        
        # Delete from Transactions (Persistent)
        if row and row[0]:
            txn_id = row[0]
            cursor.execute('DELETE FROM transactions WHERE id = ?', (txn_id,))

    @staticmethod
    def delete_position_by_id(pos_id, callback=None):
         db_worker.submit(PortfolioDB._delete_position_by_id_sql, (pos_id,), callback)

    @staticmethod
    def _update_prices_batch_sql(cursor, price_dict):
        # 1. Update Portfolio Current Prices (All lots for the symbol)
        for symbol, price in price_dict.items():
            cursor.execute('UPDATE portfolio SET current_price = ? WHERE symbol = ?', (price, symbol))
        
        # 2. Update Price History (Daily closing price)
        date_str = datetime.now().strftime("%Y-%m-%d")
        history_data = [(symbol, date_str, price) for symbol, price in price_dict.items()]
        
        cursor.executemany('''
            INSERT INTO price_history (symbol, date, price) 
            VALUES (?, ?, ?)
            ON CONFLICT(symbol, date) DO UPDATE SET price=excluded.price
        ''', history_data)

    @staticmethod
    def update_prices_batch(price_dict, callback=None):
        db_worker.submit(PortfolioDB._update_prices_batch_sql, (price_dict,), callback)

    @staticmethod
    def update_current_price(symbol, price, callback=None):
        # Deprecated in favor of batch, but kept for compatibility if needed.
        # We can implement it as a single-item batch.
        PortfolioDB.update_prices_batch({symbol: price}, callback)

    # --- Read Operations (Direct) ---

    @staticmethod
    def get_portfolio_df():
        conn = sqlite3.connect(DB_FILE)
        try:
            # We now select all lots. We alias buy_price to BuyPrice for compatibility with existing UI logic
            df = pd.read_sql_query("SELECT id, symbol as Symbol, company as Company, quantity as Quantity, buy_price as BuyPrice, buy_date as BuyDate, current_price as CurrentPrice FROM portfolio", conn)
        except Exception as e:
             logging.error(f"Error loading portfolio: {e}")
             df = pd.DataFrame()
        conn.close()
        return df


class SellDialog(ctk.CTkToplevel):
    def __init__(self, parent, symbol, current_qty, current_price, callback):
        super().__init__(parent)
        self.title(f"Vender {symbol}")
        self.geometry("350x450")
        self.callback = callback
        self.max_qty = current_qty
        
        ctk.CTkLabel(self, text=f"Vender {symbol}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(self, text=f"Disponible: {current_qty:.2f}", text_color="gray").pack()
        
        self.qty_entry = ctk.CTkEntry(self, placeholder_text="Cantidad a Vender")
        self.qty_entry.pack(pady=10)
        self.qty_entry.insert(0, str(current_qty))
        
        self.price_entry = ctk.CTkEntry(self, placeholder_text="Precio de Venta")
        self.price_entry.pack(pady=10)
        self.price_entry.insert(0, str(current_price))
        
        self.date_entry = ctk.CTkEntry(self, placeholder_text="Fecha (DD/MM/AAAA)")
        self.date_entry.pack(pady=10)
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        # Quick % Buttons
        self.percent_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.percent_frame.pack(pady=10)
        ctk.CTkButton(self.percent_frame, text="25%", width=60, command=lambda: self.set_qty(0.25)).pack(side="left", padx=5)
        ctk.CTkButton(self.percent_frame, text="50%", width=60, command=lambda: self.set_qty(0.50)).pack(side="left", padx=5)
        ctk.CTkButton(self.percent_frame, text="100%", width=60, command=lambda: self.set_qty(1.0)).pack(side="left", padx=5)

        ctk.CTkButton(self, text="Confirmar Venta", command=self.on_sell, fg_color="red", hover_color="darkred").pack(pady=20)

    def set_qty(self, percent):
        qty = self.max_qty * percent
        self.qty_entry.delete(0, 'end')
        self.qty_entry.insert(0, f"{qty:.2f}")

    def on_sell(self):
        try:
            qty = float(self.qty_entry.get())
            price = float(self.price_entry.get())
            date = self.date_entry.get().strip()
            
            if qty <= 0 or qty > self.max_qty:
                messagebox.showerror("Error", f"Cantidad inválida. Máximo: {self.max_qty}")
                return
                
            if messagebox.askyesno("Confirmar Venta", f"¿Vender {qty} de {self.title}? \nEsto es irreversible."):
                self.callback(qty, price, date)
                self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Ingrese valores numéricos válidos")

class SuggestionDialog(ctk.CTkToplevel):
    def __init__(self, parent, suggestions, callback):
        super().__init__(parent)
        self.title("Símbolo No Encontrado")
        self.geometry("300x400")
        self.suggestions = suggestions
        self.callback = callback
        
        self.label = ctk.CTkLabel(self, text="¿Quizás quisiste decir...", font=ctk.CTkFont(size=16, weight="bold"))
        self.label.pack(pady=10)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for item in suggestions:
            symbol = item['symbol']
            name = item.get('shortname') or item.get('longname') or symbol
            exch = item.get('exchange') or ""
            text = f"{symbol}\n{name} ({exch})"
            btn = ctk.CTkButton(self.scroll_frame, text=text, command=lambda s=symbol: self.on_select(s))
            btn.pack(fill="x", pady=5)
            
    def on_select(self, symbol):
        self.callback(symbol)
        self.destroy()

class EditPositionDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_data, callback):
        super().__init__(parent)
        self.title("Editar Posición")
        self.geometry("400x400")
        self.callback = callback
        
        self.data = current_data
        
        ctk.CTkLabel(self, text=f"Editar {current_data['Symbol']}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        self.qty_entry = ctk.CTkEntry(self, placeholder_text="Cantidad")
        self.qty_entry.pack(pady=10)
        self.qty_entry.insert(0, str(current_data['Quantity']))
        
        self.price_entry = ctk.CTkEntry(self, placeholder_text="Precio Compra")
        self.price_entry.pack(pady=10)
        self.price_entry.insert(0, str(current_data['BuyPrice']))

        self.date_entry = ctk.CTkEntry(self, placeholder_text="Fecha (DD/MM/AAAA)")
        self.date_entry.pack(pady=10)
        self.date_entry.insert(0, str(current_data.get('BuyDate', '')))
        
        ctk.CTkButton(self, text="Guardar Cambios", command=self.on_save, fg_color="green").pack(pady=20)
        
    def on_save(self):
        try:
            qty = float(self.qty_entry.get())
            price = float(self.price_entry.get())
            date = self.date_entry.get().strip()
            
            if not date:
                date = datetime.now().strftime("%d/%m/%Y")
                
            if messagebox.askyesno("Guardar", "¿Desea guardar los cambios?"):
                self.callback(qty, price, date)
                self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Cantidad y Precio deben ser numéricos")

class ToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.wait_time = 500     # milliseconds
        self.wrap_length = 180   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.wait_time, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = ctk.CTkToplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = ctk.CTkLabel(self.tw, text=self.text, justify='left',
                       background_color="#333333",
                       text_color="white",
                       corner_radius=4,
                       width=self.wrap_length)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

# Configuration
ctk.set_appearance_mode(config.THEME_MODE)
ctk.set_default_color_theme(config.COLOR_THEME)
DATA_FILE = config.CSV_FILE

# Helper for currency formatting (European/Latam style: 1.000,00)
def format_currency(value):
    try:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

class StockTrackerApp(ctk.CTk):
    def __init__(self) -> None:

        super().__init__()

        # Window Setup
        self.title("Rastreador de Portafolio")
        self.geometry("1250x700")

        # Layout Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data
        PortfolioDB.init_db() # Ensure tables exist (e.g. price_history)
        
        # Check if we need to migrate/rebuild for the new schema
        # A simple check: if 'portfolio' exists but has no 'buy_date' column, we drop and rebuild.
        # Or simpler: Just always rebuild on startup from transactions if we suspect schema change.
        # To be safe for this transition, let's force a rebuild if we are migrating schema.
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(portfolio)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'buy_date' not in columns:
                logging.info("Old schema detected. Rebuilding portfolio for individual positions...")
                conn.close() # Close before drop
                conn = sqlite3.connect(DB_FILE)
                conn.execute("DROP TABLE IF EXISTS portfolio")
                conn.commit()
                conn.close()
                PortfolioDB.init_db()
                PortfolioDB.rebuild_portfolio_from_transactions()
            else:
                # Check data integrity (missing transaction_ids)
                cursor.execute("SELECT count(*) FROM portfolio WHERE transaction_id IS NULL OR transaction_id = 0")
                count = cursor.fetchone()[0]
                conn.close()
                
                if count > 0:
                     logging.info(f"Detected {count} entries with missing transaction IDs. Rebuilding...")
                     PortfolioDB.rebuild_portfolio_from_transactions()
        except Exception as e:
            logging.error(f"Schema/Data check failed: {e}")

        PortfolioDB.backup_db() # Run backup before potential migration or load
        PortfolioDB.migrate_csv_if_needed()
        self.portfolio = self.load_portfolio()
        
        # UI Components
        self.create_sidebar()
        self.create_main_view()

        # State
        self.active_search_symbol = None
        self.suggestion_dialog = None
        self.row_widgets = {} # Stores references to row labels for hover effect
        
        # Filtering & Sorting State
        self.current_filter = "Todos"  # Asset type filter
        self.current_search = ""  # Search text
        self.current_sort = None  # Sort criteria
        self.compact_view = False  # View mode toggle
        self.filtered_portfolio = pd.DataFrame()  # Filtered data
        
        # Caching & Auto-Refresh State
        self.last_update_time = None
        self.refresh_job = None
        self.refresh_interval_ms = 0
        self.failed_symbols: set[str] = set() # Track failed fetches
        self.sparkline_cache_dir = config.SPARKLINE_CACHE_DIR
        if not os.path.exists(self.sparkline_cache_dir):
            os.makedirs(self.sparkline_cache_dir)
        self.sparkline_price_map = {} # Map symbol -> price used for last sparkline


        # Initial Update

        self.update_ui()

    def load_portfolio(self):
        df = PortfolioDB.get_portfolio_df()
        print(f"Loaded DataFrame: {len(df)} rows")
        if not df.empty:
            print(df.head())
        return df

    def save_portfolio(self):
        # DB handles persistence, just refresh UI
        self.portfolio = self.load_portfolio()
        self.update_ui()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(14, weight=1)  # Adjusted for new elements

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Portafolio", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Inputs
        self.symbol_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Símbolo (ej. TSLA)")
        self.symbol_entry.grid(row=1, column=0, padx=20, pady=10)

        self.company_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Empresa (Auto)")
        self.company_entry.grid(row=2, column=0, padx=20, pady=10)
        self.company_entry.configure(state="disabled")

        self.quantity_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Cantidad")
        self.quantity_entry.grid(row=3, column=0, padx=20, pady=10)

        self.price_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Precio Compra ($)")
        self.price_entry.grid(row=4, column=0, padx=20, pady=10, sticky="n")

        self.buy_date_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Fecha Compra (DD/MM/AAAA)")
        self.buy_date_entry.grid(row=5, column=0, padx=20, pady=10)

        # Price Section
        self.price_title_label = ctk.CTkLabel(self.sidebar_frame, text="Cotización Actual:", font=ctk.CTkFont(weight="bold"))
        self.price_title_label.grid(row=6, column=0, padx=20, pady=(10, 0))

        self.current_price_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="$0.00")
        self.current_price_entry.grid(row=7, column=0, padx=20, pady=(5, 5))
        self.current_price_entry.configure(state="disabled")

        self.price_time_label = ctk.CTkLabel(self.sidebar_frame, text="--/--/-- --:--", font=ctk.CTkFont(size=12))
        self.price_time_label.grid(row=8, column=0, padx=20, pady=(0, 10))

        # Buttons
        self.add_button = ctk.CTkButton(self.sidebar_frame, text="Agregar Posición", command=self.add_position)
        self.add_button.grid(row=9, column=0, padx=20, pady=10)

        self.update_button = ctk.CTkButton(self.sidebar_frame, text="Actualizar Datos", command=self.manual_update, fg_color="green")
        self.update_button.grid(row=10, column=0, padx=20, pady=(10, 5))

        # Last Update Label
        self.last_update_label = ctk.CTkLabel(self.sidebar_frame, text="Última act: --:--", font=ctk.CTkFont(size=12))
        self.last_update_label.grid(row=11, column=0, padx=20, pady=(0, 10))

        # Auto-Refresh Menu
        self.refresh_label = ctk.CTkLabel(self.sidebar_frame, text="Auto-Refresh:", font=ctk.CTkFont(size=12, weight="bold"))
        self.refresh_label.grid(row=12, column=0, padx=20, pady=(10, 0))
        
        self.refresh_option = ctk.CTkOptionMenu(self.sidebar_frame, values=["Off", "5 min", "10 min", "15 min"],
                                                command=self.change_refresh_interval)
        self.refresh_option.grid(row=13, column=0, padx=20, pady=(0, 20))
        self.refresh_option.set("Off")

        self.exchange_rate_label = ctk.CTkLabel(self.sidebar_frame, text="USD/ARS: ---", font=ctk.CTkFont(size=12, weight="bold"))
        self.exchange_rate_label.grid(row=14, column=0, padx=20, pady=(0, 20))

        # Bindings for auto-lookup
        self.symbol_entry.bind("<FocusOut>", self.on_symbol_focus_out)
        self.symbol_entry.bind("<Return>", self.on_symbol_focus_out)

    def on_symbol_focus_out(self, event=None) -> None:
        symbol = self.symbol_entry.get().strip().upper()
        # Prevent re-fetching if we are already dealing with this symbol or a dialog is open
        if symbol and symbol != self.active_search_symbol:
            if self.suggestion_dialog and self.suggestion_dialog.winfo_exists():
                return
                
            self.active_search_symbol = symbol
            threading.Thread(target=self.fetch_stock_info_sidebar, args=(symbol,), daemon=True).start()

    def fetch_stock_info_sidebar(self, symbol: str) -> None:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if valid
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            
            if not price:
                raise ValueError("No price found")

            name = info.get('longName') or info.get('shortName') or ""
            
            # Time
            market_time = info.get('regularMarketTime')
            if market_time:
                time_str = datetime.fromtimestamp(market_time).strftime('%d/%m/%Y %H:%M')
            else:
                time_str = datetime.now().strftime('%d/%m/%Y %H:%M')

            # Update UI in main thread
            self.after(0, lambda: self.update_sidebar_info(name, price, time_str))
            self.active_search_symbol = None # Reset
            
        except Exception:
            # If fetch fails, try to search for suggestions
            self.search_symbols(symbol)

    def search_symbols(self, query: str) -> None:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            data = response.json()
            
            suggestions = []
            if 'quotes' in data:
                for q in data['quotes']:
                    if q.get('quoteType') == 'EQUITY' or q.get('quoteType') == 'ETF':
                         suggestions.append(q)
            
            if suggestions:
                self.after(0, lambda: self.show_suggestions(suggestions))
        except Exception as e:
            logging.error(f"Search failed: {e}")

    def show_suggestions(self, suggestions):
        if self.suggestion_dialog and self.suggestion_dialog.winfo_exists():
            self.suggestion_dialog.destroy()
        self.suggestion_dialog = SuggestionDialog(self, suggestions, self.on_suggestion_selected)

    def on_suggestion_selected(self, symbol):
        self.active_search_symbol = None # Reset to allow fetch of new symbol
        self.symbol_entry.delete(0, 'end')
        self.symbol_entry.insert(0, symbol)
        # Trigger fetch again
        threading.Thread(target=self.fetch_stock_info_sidebar, args=(symbol,), daemon=True).start()

    def update_sidebar_info(self, name, price, time_str=""):
        # Update Company Name
        if name:
            self.company_entry.configure(state="normal")
            self.company_entry.delete(0, 'end')
            self.company_entry.insert(0, name)
            self.company_entry.configure(state="disabled")
        
        # Update Current Price field
        self.current_price_entry.configure(state="normal")
        self.current_price_entry.delete(0, 'end')
        self.current_price_entry.insert(0, f"${price:,.2f}")
        self.current_price_entry.configure(state="disabled")
        
        # Update Time
        if time_str:
            self.price_time_label.configure(text=time_str)

    def create_main_view(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Summary Cards
        self.summary_frame = ctk.CTkFrame(self.main_frame)
        self.summary_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total_invested = self.create_summary_card(self.summary_frame, "Total Invertido", "$0,00", 0)
        self.card_current_value = self.create_summary_card(self.summary_frame, "Valor Actual", "$0,00", 1)
        self.card_total_usd = self.create_summary_card(self.summary_frame, "Valor Total (USD)", "USD 0,00", 2)
        self.card_profit_loss = self.create_summary_card(self.summary_frame, "G/P Total", "$0,00 (0,00%)", 3)

        # Controls Bar
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.controls_frame.grid_columnconfigure(1, weight=1)
        
        # Search
        self.search_entry = ctk.CTkEntry(self.controls_frame, placeholder_text="🔍 Buscar símbolo o empresa...", width=250)
        self.search_entry.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_entry.bind("<KeyRelease>", self.on_search_change)
        
        # Asset Type Filter
        self.filter_menu = ctk.CTkOptionMenu(
            self.controls_frame, 
            values=["Todos", "US Stocks", "CEDEARs", "Crypto"],
            command=self.on_filter_change,
            width=140
        )
        self.filter_menu.grid(row=0, column=1, padx=5, pady=5)
        self.filter_menu.set("Todos")
        
        # Sort Buttons
        sort_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        sort_frame.grid(row=0, column=2, padx=5, pady=5)
        
        ctk.CTkLabel(sort_frame, text="Ordenar:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        
        self.sort_gain_btn = ctk.CTkButton(
            sort_frame, text="Ganancia %", width=100, height=28,
            command=lambda: self.on_sort_change('Ganancia %')
        )
        self.sort_gain_btn.pack(side="left", padx=2)
        
        self.sort_value_btn = ctk.CTkButton(
            sort_frame, text="Valor", width=80, height=28,
            command=lambda: self.on_sort_change('Valor')
        )
        self.sort_value_btn.pack(side="left", padx=2)
        
        self.sort_symbol_btn = ctk.CTkButton(
            sort_frame, text="Símbolo", width=80, height=28,
            command=lambda: self.on_sort_change('Símbolo')
        )
        self.sort_symbol_btn.pack(side="left", padx=2)
        
        # View Toggle
        self.view_toggle_btn = ctk.CTkButton(
            self.controls_frame, 
            text="Vista: Detallada", 
            width=130, 
            height=28,
            command=self.toggle_view,
            fg_color="#555",
            hover_color="#666"
        )
        self.view_toggle_btn.grid(row=0, column=3, padx=5, pady=5, sticky="e")

        # Export Button
        self.export_btn = ctk.CTkButton(
            self.controls_frame, 
            text="Exportar", 
            width=80, 
            height=28,
            command=self.export_to_excel,
            fg_color="#336633",
            hover_color="#447744"
        )
        self.export_btn.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        # Aggregated Summary Area (Replaces Chart)
        self.agg_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Resumen por Acción", height=150)
        self.agg_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.agg_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Headers for Aggregated Table
        agg_headers = ["Acción", "Cant. Total", "P. Prom. Compra", "Precio Actual", "Total General", "Total USD"]
        for i, header in enumerate(agg_headers):
            ctk.CTkLabel(self.agg_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=5, pady=5)

        # Table Area (Scrollable Frame mimicking a table)
        self.table_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Tus Posiciones")
        self.table_frame.grid(row=3, column=0, padx=20, pady=20, sticky="nsew")
        self.table_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=1) # Added one more column for BuyDate

        # Table Headers
        headers = ["Símbolo", "Empresa", "Trend (1m)", "Riesgo", "Cant.", "P. Compra", "Fecha Compra", "P. Actual", "Valor", "G/P", "Acciones"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=5, pady=5)

    def create_summary_card(self, parent, title, value, col):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=col, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=14)).pack(pady=(10, 0))
        value_label = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=20, weight="bold"))
        value_label.pack(pady=(0, 10))
        return value_label

    def add_position(self):
        symbol = self.symbol_entry.get().upper().strip()
        company = self.company_entry.get().strip()
        quantity = self.quantity_entry.get().strip()
        price = self.price_entry.get().strip()
        buy_date = self.buy_date_entry.get().strip()
        
        if not buy_date:
            buy_date = datetime.now().strftime("%d/%m/%Y")

        if not symbol or not quantity or not price:
            messagebox.showerror("Error", "Complete Símbolo, Cantidad y Precio")
            return

        try:
            quantity = float(quantity)
            price = float(price)
        except ValueError:
            messagebox.showerror("Error", "Cantidad y Precio deben ser numéricos")
            return

        # Auto-fetch if still empty (fallback if focus out didn't work or user was fast)
        if not company:
             # Basic sync fetch if missing
             try:
                 ticker = yf.Ticker(symbol)
                 current_info = ticker.info
                 company = current_info.get('longName') or current_info.get('shortName') or symbol
             except:
                 company = symbol
        
        # Async Add
        PortfolioDB.add_transaction(symbol, company, 'BUY', quantity, price, buy_date, 
                                    callback=lambda _: self.after(0, self.save_portfolio))

        # Auto-fetch current market price in background
        threading.Thread(target=self.fetch_single_price_update, args=(symbol,), daemon=True).start()
        
        # Clear inputs
        self.symbol_entry.delete(0, 'end')
        
        self.company_entry.configure(state="normal")
        self.company_entry.delete(0, 'end')
        self.company_entry.configure(state="disabled")
        
        self.quantity_entry.delete(0, 'end')
        self.price_entry.delete(0, 'end')
        self.buy_date_entry.delete(0, 'end')
        
        # Auto-focus for rapid entry
        self.symbol_entry.focus_set()

    def delete_row(self, db_id):
        if messagebox.askyesno("Eliminar", "¿Seguro que deseas eliminar esta posición?"):
            PortfolioDB.delete_position_by_id(db_id, callback=lambda _: self.after(0, self.save_portfolio))
            
    def edit_position(self, row):
        EditPositionDialog(self, row, lambda q, p, d: self.save_edited_position(row['id'], q, p, d))
        
    def save_edited_position(self, pos_id, quantity, price, date):
        PortfolioDB.update_position_by_id(pos_id, quantity, price, date, callback=lambda _: self.after(0, self.save_portfolio))

    def open_sell_dialog(self, row):
        # Current price fallback
        price = row['CurrentPrice'] if row['CurrentPrice'] > 0 else row['BuyPrice']
        SellDialog(self, row['Symbol'], row['Quantity'], price, 
                   lambda q, p, d: self.save_sell(row['Symbol'], row['Company'], q, p, d))

    def save_sell(self, symbol, company, quantity, price, date):
        PortfolioDB.add_transaction(symbol, company, 'SELL', quantity, price, date, 
                                    callback=lambda _: self.after(0, self.save_portfolio))

    def remove_position(self):
        pass # Deprecated

    def manual_update(self):
        # Force update regardless of cache
        self.start_market_update(force=True)

    def change_refresh_interval(self, selection):
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None
            
        if selection == "Off":
            return
            
        self.refresh_interval_ms = config.REFRESH_INTERVAL_MAP.get(selection, 0)
        self.schedule_auto_refresh()

    def schedule_auto_refresh(self):
        if self.refresh_interval_ms > 0:
            self.refresh_job = self.after(self.refresh_interval_ms, self.auto_refresh_task)

    def auto_refresh_task(self):
        self.start_market_update(force=True) # Auto-refresh implies we want new data
        self.schedule_auto_refresh()

    def start_market_update(self, force=False):
        if self.portfolio.empty:
            return
        
        # Cache Check
        CACHE_DURATION = config.CACHE_DURATION_SECONDS
        if not force and self.last_update_time:
            elapsed = (datetime.now() - self.last_update_time).total_seconds()
            if elapsed < CACHE_DURATION:
                logging.info("Using cached data")
                # Even if cached, we might want to refresh UI if something changed locally
                self.update_ui()
                return

        self.update_button.configure(state="disabled", text="Actualizando...")
        self.exchange_rate_label.configure(text="USD/ARS: Calculando...")
        thread = threading.Thread(target=self.fetch_market_data)
        thread.start()

    def get_sparkline_path(self, symbol):
        return os.path.join(self.sparkline_cache_dir, f"{symbol}_spark.png")

    def retry_request(self, func, retries=3, *args, **kwargs):
        """Retry a function with exponential backoff"""
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == retries - 1:
                    raise e
                wait = (2 ** i) + random.uniform(0, 1)
                logging.warning(f"Retrying {func.__name__} in {wait:.2f}s due to {e}")
                time.sleep(wait)

    def fetch_market_data(self) -> None:
        try:

            symbols = self.portfolio["Symbol"].unique().tolist()
            if not symbols:
                return

            tickers = yf.Tickers(" ".join(symbols))
            current_prices = {}
            new_sparklines = {}
            new_volatility = {}
            self.failed_symbols.clear() # Reset failures on new fetch
            
            # Use Agg backend for non-GUI plot generation
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            from PIL import Image

            for symbol in symbols:
                try:
                    # Access the ticker securely
                    ticker = tickers.tickers[symbol] if len(symbols) > 1 else tickers
                    
                    # Fetch history for Sparklines (1mo for better trend)
                    # We employ caching logic here to avoid regenerating sparklines if price hasn't moved significantly
                    # or if we have a recent valid cache.
                    
                    # 1. Fetch History with Retry
                    hist = self.retry_request(ticker.history, period="1mo")
                    
                    if not hist.empty:
                        # 1. Current Price
                        current_price = hist["Close"].iloc[-1]
                        current_prices[symbol] = current_price
                        
                        # 2. Volatility (Risk) - Std Dev of daily returns

                        # We use pct_change() to get returns, then std()
                        if len(hist) > 5:
                            daily_returns = hist["Close"].pct_change().dropna()
                            vol = daily_returns.std() * 100 # percentage
                            new_volatility[symbol] = vol
                        else:
                            new_volatility[symbol] = 0

                        # 3. Sparkline Generation
                        # Check cache validity
                        cache_path = self.get_sparkline_path(symbol)
                        last_price = self.sparkline_price_map.get(symbol, 0)
                        
                        # Regenerate if:
                        # - No cache file
                        # - Price changed > 0.1% from last generation (significant change)
                        # - or simple logic: just reuse if file exists and is recent (< 1 hour)?
                        # Let's use price change + file existence
                        
                        regenerate = True
                        if os.path.exists(cache_path):
                            if abs(current_price - last_price) / (last_price if last_price else 1) < 0.001:
                                regenerate = False
                        
                        if regenerate:
                            # Create a small figure
                            fig = plt.figure(figsize=(2, 0.5), dpi=80) # Small size
                            ax = fig.add_subplot(111)
                            
                            # Plot line
                            color = 'green' if hist["Close"].iloc[-1] >= hist["Close"].iloc[0] else 'red'
                            ax.plot(hist.index, hist["Close"], color=color, linewidth=1.5)
                            
                            # Remove axes and margins
                            ax.axis('off')

                            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                            
                            # Save to disk cache
                            plt.savefig(cache_path, format='png', transparent=True)
                            plt.close(fig) # Close to free memory
                            
                            self.sparkline_price_map[symbol] = current_price
                        
                        # Load from disk
                        if os.path.exists(cache_path):
                            img_pil = Image.open(cache_path)
                            new_sparklines[symbol] = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(100, 25))
                        
                    else:
                        current_prices[symbol] = 0
                        new_volatility[symbol] = 0
                except Exception as e:
                    logging.error(f"Failed to fetch/plot {symbol}: {e}")
                    current_prices[symbol] = 0
                    self.failed_symbols.add(symbol)

            # Store visual data in app state (not DB)
            self.sparklines = new_sparklines
            self.volatility_map = new_volatility

            # Fetch USD/ARS exchange rate
            self.ars_rate = 0
            self.rate_source = ""
            
            # Try 1: CryptoYa (USDT as proxy for Blue/CCL) or Binance - PREFERRED
            try:
                r = self.retry_request(requests.get, retries=3, url="https://criptoya.com/api/binance/usdt/ars/1.0", timeout=5)
                data = r.json()
                # data is like {'ask': 1120.5, 'bid': 1118.0, ...}
                if 'ask' in data:
                    self.ars_rate = data['ask']
                    self.rate_source = "USDT (Binance)"
            except Exception as e:
                logging.error(f"Failed to fetch from CryptoYa: {e}")

            # Try 2: DolarAPI (Blue) if Binance failed
            if self.ars_rate == 0:
                try:
                    r = self.retry_request(requests.get, retries=3, url="https://dolarapi.com/v1/dolares/blue", timeout=5)
                    data = r.json()
                    self.ars_rate = data['venta']
                    self.rate_source = "Blue"
                except Exception as e:
                    logging.error(f"Failed to fetch from DolarAPI: {e}")

            # Try 3: yfinance if others failed
            if self.ars_rate == 0:
                try:
                    ars_ticker = yf.Ticker("ARS=X")
                    ars_hist = self.retry_request(ars_ticker.history, period="1d")
                    if not ars_hist.empty:
                        self.ars_rate = ars_hist["Close"].iloc[-1]
                        self.rate_source = "Yahoo"
                except:
                    pass

            # Update dataframe safely
            self.portfolio["CurrentPrice"] = self.portfolio["Symbol"].map(current_prices).fillna(0)
            
            # Update DB with new prices (BATCH)
            PortfolioDB.update_prices_batch(current_prices)

            # Schedule UI update on main thread
            self.after(0, self.update_ui_after_fetch)
            
        except Exception as e:
            logging.error(f"Error fetching data: {e}")
        finally:
            self.after(0, lambda: self.update_button.configure(state="normal", text="Actualizar Datos"))

    def update_ui_after_fetch(self):
        self.last_update_time = datetime.now()
        self.last_update_label.configure(text=f"Última act: {self.last_update_time.strftime('%H:%M:%S')}")
        
        self.save_portfolio() # Save the fetched prices too if we want, or just re-render
        if hasattr(self, 'ars_rate') and self.ars_rate > 0:
            source_text = f" ({self.rate_source})" if self.rate_source else ""
            self.exchange_rate_label.configure(text=f"USD/ARS{source_text}: ${self.ars_rate:,.2f}")
        else:
            self.exchange_rate_label.configure(text="USD/ARS: No disponible")
        self.update_ui()

    def fetch_single_price_update(self, symbol):
        # We also need to update this to fetch history for sparklines if we want consistency,
        # but for speed on "Add", we might skip sparkline until full refresh or do it here.
        # For simplicity, we'll just do price here. Sparkline will come on next full refresh.
        try:
            ticker = yf.Ticker(symbol)
            # Try fast history first
            hist = ticker.history(period="1d")
            price = 0
            if not hist.empty:
                price = hist["Close"].iloc[-1]
            else:
                # Fallback to info
                info = ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0
            
            if price > 0:
                # We must use a callback to ensure DB is updated before we reload/refresh UI
                PortfolioDB.update_current_price(symbol, price, callback=lambda _: self.after(0, self.save_portfolio))
        except Exception as e:
            logging.error(f"Auto-fetch error for {symbol}: {e}")

    def update_ui(self) -> None:
        # Calculation
        if "CurrentPrice" not in self.portfolio.columns:
            self.portfolio["CurrentPrice"] = 0.0

        self.portfolio["Value"] = self.portfolio["Quantity"] * self.portfolio["CurrentPrice"]
        self.portfolio["Invested"] = self.portfolio["Quantity"] * self.portfolio["BuyPrice"]
        self.portfolio["ProfitLoss"] = self.portfolio["Value"] - self.portfolio["Invested"]
        
        # Calculate % for entire portfolio (will be used for filter/sort too)
        self.portfolio["ProfitPct"] = self.portfolio.apply(
            lambda x: (x["ProfitLoss"] / x["Invested"] * 100) if x["Invested"] > 0 else 0, axis=1
        )

        # Apply filters and sorting
        display_df = self.apply_filters_and_sort()

        # Calculate totals from FILTERED data
        total_invested = display_df["Invested"].sum() if not display_df.empty else 0
        total_value = display_df["Value"].sum() if not display_df.empty else 0
        total_pl = display_df["ProfitLoss"].sum() if not display_df.empty else 0
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

        # Calculate totals from FILTERED data
        total_invested = display_df["Invested"].sum() if not display_df.empty else 0
        total_value = display_df["Value"].sum() if not display_df.empty else 0
        total_pl = display_df["ProfitLoss"].sum() if not display_df.empty else 0
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

        # Update Cards
        self.card_total_invested.configure(text=f"${format_currency(total_invested)}")
        self.card_current_value.configure(text=f"${format_currency(total_value)}")
        
        total_usd = total_value / self.ars_rate if hasattr(self, 'ars_rate') and self.ars_rate > 0 else 0
        self.card_total_usd.configure(text=f"USD {format_currency(total_usd)}")

        color = "green" if total_pl >= 0 else "red"
        self.card_profit_loss.configure(text=f"${format_currency(total_pl)} ({total_pl_pct:.2f}%)", text_color=color)

        # Update Table
        # clear existing rows and widget cache
        self.row_widgets = {}
        for widget in self.table_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0: # Skip header
                widget.destroy()

        # Update table headers based on view mode
        if self.compact_view:
            headers = ["Símbolo", "Empresa", "Cant.", "P. Actual", "G/P", "Acciones"]
        else:
            headers = ["Símbolo", "Empresa", "Trend (1m)", "Riesgo", "Cant.", "P. Compra", "Fecha Compra", "P. Actual", "Valor", "G/P", "Acciones"]
        
        # Clear and recreate headers
        for widget in self.table_frame.winfo_children():
            if int(widget.grid_info()["row"]) == 0:
                widget.destroy()
        
        for i, header in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=5, pady=5)

        # Render rows from filtered dataframe
        for idx, (index, row) in enumerate(display_df.iterrows()):
            r = idx + 1
            self.row_widgets[index] = []
            
            # Data Preparation
            pl_color = "#00FF00" if row['ProfitLoss'] >= 0 else "#FF4444" 
            comp_name = str(row.get("Company", ""))
            if len(comp_name) > 15: comp_name = comp_name[:15] + "..."
            
            symbol = row["Symbol"]
            col = 0  # Column counter for compact view
            
            # --- Column: Symbol ---
            lbl_sym = ctk.CTkLabel(self.table_frame, text=str(symbol), text_color="white", width=60)
            lbl_sym.grid(row=r, column=col, padx=5, pady=2)
            self.row_widgets[index].append(lbl_sym)
            col += 1

            # --- Column: Company ---
            lbl_comp = ctk.CTkLabel(self.table_frame, text=comp_name, text_color="silver", width=120)
            lbl_comp.grid(row=r, column=col, padx=5, pady=2)
            self.row_widgets[index].append(lbl_comp)
            col += 1

            if not self.compact_view:
                # --- Column: Sparkline (Trend) ---
                spark_label = ctk.CTkLabel(self.table_frame, text="")
                if hasattr(self, 'sparklines') and symbol in self.sparklines:
                    spark_label.configure(image=self.sparklines[symbol], text="")
                else:
                    spark_label.configure(text="---")
                spark_label.grid(row=r, column=col, padx=5, pady=2)
                self.row_widgets[index].append(spark_label)
                col += 1

                # --- Column: Risk (Volatility) ---
                vol_val = self.volatility_map.get(symbol, 0) if hasattr(self, 'volatility_map') else 0
                if vol_val < config.VOLATILITY_LOW:
                    risk_color = "green"
                    risk_char = "●"
                elif vol_val < config.VOLATILITY_HIGH:
                    risk_color = "yellow"
                    risk_char = "●"
                else:
                    risk_color = "red"
                    risk_char = "●"

                lbl_risk = ctk.CTkLabel(self.table_frame, text=f"{risk_char} {vol_val:.1f}%", text_color=risk_color)
                lbl_risk.grid(row=r, column=col, padx=5, pady=2)
                self.row_widgets[index].append(lbl_risk)
                col += 1

            # --- Column: Quantity ---
            lbl_qty = ctk.CTkLabel(self.table_frame, text=f"{row['Quantity']:.2f}", text_color="white")
            lbl_qty.grid(row=r, column=col, padx=5, pady=2)
            self.row_widgets[index].append(lbl_qty)
            col += 1
            
            if not self.compact_view:
                # --- Column: Buy Price ---
                lbl_buy = ctk.CTkLabel(self.table_frame, text=f"${format_currency(row['BuyPrice'])}", text_color="white")
                lbl_buy.grid(row=r, column=col, padx=5, pady=2)
                self.row_widgets[index].append(lbl_buy)
                col += 1

                # --- Column: Buy Date (NEW) ---
                lbl_buy_date = ctk.CTkLabel(self.table_frame, text=str(row.get('BuyDate', '-')), text_color="white")
                lbl_buy_date.grid(row=r, column=col, padx=5, pady=2)
                self.row_widgets[index].append(lbl_buy_date)
                col += 1

            # --- Column: Current Price ---
            price_text = f"${format_currency(row['CurrentPrice'])}"
            price_color = "white"
            if symbol in self.failed_symbols:
                price_text = "⚠️ Error"
                price_color = "gray"
                
            lbl_curr = ctk.CTkLabel(self.table_frame, text=price_text, text_color=price_color)
            lbl_curr.grid(row=r, column=col, padx=5, pady=2)
            self.row_widgets[index].append(lbl_curr)
            col += 1

            if not self.compact_view:
                # --- Column: Value ---
                lbl_val = ctk.CTkLabel(self.table_frame, text=f"${format_currency(row['Value'])}", text_color="white", font=ctk.CTkFont(weight="bold"))
                lbl_val.grid(row=r, column=col, padx=5, pady=2)
                self.row_widgets[index].append(lbl_val)
                col += 1

            # --- Column: Profit/Loss ---
            pct_text = f"({row['ProfitPct']:.2f}%)"
            lbl_pl = ctk.CTkLabel(self.table_frame, text=f"${format_currency(row['ProfitLoss'])} {pct_text}", text_color=pl_color, font=ctk.CTkFont(weight="bold"))
            lbl_pl.grid(row=r, column=col, padx=5, pady=2)
            self.row_widgets[index].append(lbl_pl)
            col += 1
            
            # Only add tooltips if we added the Risk column (length check)
            if not self.compact_view and len(self.row_widgets[index]) > 3: 
                 # Risk is at index 3: [Sym, Comp, Spark, Risk, ...]
                 risk_widget = self.row_widgets[index][3]
                 
                 risk_msg = f"Riesgo Bajo (<{config.VOLATILITY_LOW}%)"
                 if "yellow" in str(risk_widget.cget("text_color")): risk_msg = f"Riesgo Medio ({config.VOLATILITY_LOW}% - {config.VOLATILITY_HIGH}%)"
                 if "red" in str(risk_widget.cget("text_color")): risk_msg = f"Riesgo Alto (>{config.VOLATILITY_HIGH}%)"
                 
                 if "●" in risk_widget.cget("text"):
                     ToolTip(risk_widget, risk_msg)

            # --- Column: Actions ---
            btn_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent", width=100)
            btn_frame.grid(row=r, column=col, padx=5, pady=2)
            
            # Edit
            ctk.CTkButton(btn_frame, text="✎", width=30, height=20, fg_color="#444", 
                          command=lambda r=row: self.edit_position(r)).pack(side="left", padx=2)
            # Sell
            ctk.CTkButton(btn_frame, text="$", width=30, height=20, fg_color="orange", hover_color="darkorange",
                          command=lambda r=row: self.open_sell_dialog(r)).pack(side="left", padx=2)
            # Delete
            ctk.CTkButton(btn_frame, text="X", width=30, height=20, fg_color="#600", hover_color="#800", 
                          command=lambda i=row['id']: self.delete_row(i)).pack(side="left", padx=2)          
        
        # Update Summary Table
        self.update_summary_table()
    
    def on_row_hover(self, index, is_hover):
        color = "#333333" if is_hover else "transparent"
        if index in self.row_widgets:
            for widget in self.row_widgets[index]:
                try:
                    widget.configure(fg_color=color)
                except:
                    pass
    
    def on_search_change(self, event=None):
        """Handle search input changes"""
        self.current_search = self.search_entry.get().strip()
        self.update_ui()
    
    def on_filter_change(self, value):
        """Handle asset type filter changes"""
        self.current_filter = value
        self.update_ui()
    
    def on_sort_change(self, criteria):
        """Handle sort button clicks"""
        # Toggle sort if clicking same button
        if self.current_sort == criteria:
            self.current_sort = None
        else:
            self.current_sort = criteria
        
        # Update button colors to show active sort
        default_color = ["#3B8ED0", "#1F6AA5"]  # CTk default blue
        active_color = ["#2ECC71", "#27AE60"]   # Green for active
        
        self.sort_gain_btn.configure(fg_color=active_color if self.current_sort == 'Ganancia %' else default_color[0],
                                      hover_color=active_color[1] if self.current_sort == 'Ganancia %' else default_color[1])
        self.sort_value_btn.configure(fg_color=active_color if self.current_sort == 'Valor' else default_color[0],
                                       hover_color=active_color[1] if self.current_sort == 'Valor' else default_color[1])
        self.sort_symbol_btn.configure(fg_color=active_color if self.current_sort == 'Símbolo' else default_color[0],
                                        hover_color=active_color[1] if self.current_sort == 'Símbolo' else default_color[1])
        
        self.update_ui()
    
    def toggle_view(self):
        """Toggle between compact and detailed view"""
        self.compact_view = not self.compact_view
        view_text = "Vista: Compacta" if self.compact_view else "Vista: Detallada"
        self.view_toggle_btn.configure(text=view_text)
        self.update_ui()

    def get_asset_type(self, symbol):
        """Detect asset type based on symbol"""
        symbol = str(symbol).upper()
        if symbol.endswith('.BA'):
            return 'CEDEARs'
        elif any(crypto in symbol for crypto in ['BTC', 'ETH', 'DOGE', 'ADA', 'SOL', 'XRP', '-USD']):
            return 'Crypto'
        else:
            return 'US Stocks'
    
    def apply_filters_and_sort(self):
        """Apply current filters, search, and sorting to portfolio"""
        df = self.portfolio.copy()
        
        # Apply asset type filter
        if self.current_filter != "Todos":
            df['AssetType'] = df['Symbol'].apply(self.get_asset_type)
            df = df[df['AssetType'] == self.current_filter]
        
        # Apply search filter
        if self.current_search:
            search_term = self.current_search.lower()
            mask = (df['Symbol'].str.lower().str.contains(search_term, na=False) | 
                    df['Company'].str.lower().str.contains(search_term, na=False))
            df = df[mask]
        
        # Apply sorting
        if self.current_sort == 'Ganancia %':
            # ProfitPct is already calculated in update_ui, but if called from elsewhere make sure it exists
            if 'ProfitPct' not in df.columns:
                 df['ProfitPct'] = df.apply(lambda x: (x['ProfitLoss'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)
            df = df.sort_values('ProfitPct', ascending=False)
        elif self.current_sort == 'Valor':
            df = df.sort_values('Value', ascending=False)
        elif self.current_sort == 'Símbolo':
            df = df.sort_values('Symbol', ascending=True)
        
        self.filtered_portfolio = df
        return df
    
    def update_summary_table(self):
        # Clear existing rows
        for widget in self.agg_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0: # Skip header
                widget.destroy()

        if self.portfolio.empty:
            return

        # Aggregation Logic
        # Group by Symbol
        grouped = self.portfolio.groupby('Symbol').apply(
            lambda x: pd.Series({
                'TotalQuantity': x['Quantity'].sum(),
                'WeightedAvgPrice': (x['Quantity'] * x['BuyPrice']).sum() / x['Quantity'].sum() if x['Quantity'].sum() > 0 else 0,
                'CurrentPrice': x['CurrentPrice'].iloc[0] if not x['CurrentPrice'].empty else 0,
                'TotalValue': x['Value'].sum()
            })
        ).reset_index()

        # Render rows
        for index, row in grouped.iterrows():
            r = index + 1
            total_val_usd = row['TotalValue'] / self.ars_rate if hasattr(self, 'ars_rate') and self.ars_rate > 0 else 0
            
            ctk.CTkLabel(self.agg_frame, text=row['Symbol']).grid(row=r, column=0, padx=5, pady=2)
            ctk.CTkLabel(self.agg_frame, text=f"{row['TotalQuantity']:.2f}").grid(row=r, column=1, padx=5, pady=2)
            ctk.CTkLabel(self.agg_frame, text=f"${format_currency(row['WeightedAvgPrice'])}").grid(row=r, column=2, padx=5, pady=2)
            ctk.CTkLabel(self.agg_frame, text=f"${format_currency(row['CurrentPrice'])}").grid(row=r, column=3, padx=5, pady=2)
            ctk.CTkLabel(self.agg_frame, text=f"${format_currency(row['TotalValue'])}").grid(row=r, column=4, padx=5, pady=2)
            ctk.CTkLabel(self.agg_frame, text=f"USD {format_currency(total_val_usd)}").grid(row=r, column=5, padx=5, pady=2)

    def export_to_excel(self):
        if self.portfolio.empty:
            messagebox.showinfo("Exportar", "No hay datos para exportar")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                   filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if file_path:
            try:
                # Create a clean export version
                export_df = self.portfolio.copy()
                
                # Ensure calculated columns exist
                if "Value" not in export_df.columns:
                     export_df["Value"] = export_df["Quantity"] * export_df["CurrentPrice"]
                if "Invested" not in export_df.columns:
                     export_df["Invested"] = export_df["Quantity"] * export_df["BuyPrice"]
                if "ProfitLoss" not in export_df.columns:
                     export_df["ProfitLoss"] = export_df["Value"] - export_df["Invested"]
                if "ProfitPct" not in export_df.columns:
                     export_df['ProfitPct'] = export_df.apply(lambda x: (x['ProfitLoss'] / x['Invested'] * 100) if x['Invested'] > 0 else 0, axis=1)

                # Select and rename columns for clarity
                export_df = export_df[['Symbol', 'Company', 'Quantity', 'BuyPrice', 'CurrentPrice', 'Value', 'Invested', 'ProfitLoss', 'ProfitPct']]
                export_df.columns = ['Símbolo', 'Empresa', 'Cantidad', 'Precio Compra', 'Precio Actual', 'Valor Total', 'Invertido', 'Ganancia/Pérdida ($)', 'Ganancia/Pérdida (%)']
                
                export_df.to_excel(file_path, index=False)
                messagebox.showinfo("Exportar", "Datos exportados correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar: {e}")

if __name__ == "__main__":
    app = StockTrackerApp()
    app.mainloop()
