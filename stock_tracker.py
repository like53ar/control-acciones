import customtkinter as ctk
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import threading
from tkinter import messagebox
import requests
from datetime import datetime

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

# Configuration
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
DATA_FILE = "cartera.csv"

class StockTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Rastreador de Portafolio")
        self.geometry("1250x700")

        # Layout Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data
        self.portfolio = self.load_portfolio()
        
        # UI Components
        self.create_sidebar()
        self.create_main_view()

        # State
        self.active_search_symbol = None
        self.suggestion_dialog = None
        self.row_widgets = {} # Stores references to row labels for hover effect

        # Initial Update
        self.update_ui()

    def load_portfolio(self):
        if os.path.exists(DATA_FILE):
            try:
                return pd.read_csv(DATA_FILE)
            except Exception as e:
                print(f"Error loading data: {e}")
                return pd.DataFrame(columns=["Symbol", "Company", "Quantity", "BuyPrice", "BuyDate"])
        else:
            return pd.DataFrame(columns=["Symbol", "Company", "Quantity", "BuyPrice", "BuyDate"])

    def save_portfolio(self):
        self.portfolio.to_csv(DATA_FILE, index=False)
        self.update_ui()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(11, weight=1)

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

        self.price_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Precio Compra (USD)")
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

        # self.remove_button removed as we moved to row-based deletion

        self.update_button = ctk.CTkButton(self.sidebar_frame, text="Actualizar Datos", command=self.start_market_update, fg_color="green")
        self.update_button.grid(row=10, column=0, padx=20, pady=(10, 20))

        # Bindings for auto-lookup
        self.symbol_entry.bind("<FocusOut>", self.on_symbol_focus_out)
        self.symbol_entry.bind("<Return>", self.on_symbol_focus_out)

    def on_symbol_focus_out(self, event=None):
        symbol = self.symbol_entry.get().strip().upper()
        # Prevent re-fetching if we are already dealing with this symbol or a dialog is open
        if symbol and symbol != self.active_search_symbol:
            if self.suggestion_dialog and self.suggestion_dialog.winfo_exists():
                return
                
            self.active_search_symbol = symbol
            threading.Thread(target=self.fetch_stock_info_sidebar, args=(symbol,), daemon=True).start()

    def fetch_stock_info_sidebar(self, symbol):
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

    def search_symbols(self, query):
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
            print(f"Search failed: {e}")

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
        self.summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_total_invested = self.create_summary_card(self.summary_frame, "Total Invertido", "$0.00", 0)
        self.card_current_value = self.create_summary_card(self.summary_frame, "Valor Actual", "$0.00", 1)
        self.card_profit_loss = self.create_summary_card(self.summary_frame, "G/P Total", "$0.00 (0.00%)", 2)

        # Chart Area
        self.chart_frame = ctk.CTkFrame(self.main_frame)
        self.chart_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)

        # Table Area (Scrollable Frame mimicking a table)
        self.table_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Tus Posiciones")
        self.table_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        self.table_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8), weight=1)

        # Table Headers
        headers = ["Símbolo", "Empresa", "Cant.", "P. Compra", "F. Compra", "P. Actual", "Valor", "G/P", "Acciones"]
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
        
        new_row = pd.DataFrame([[symbol, company, quantity, price, buy_date]], columns=["Symbol", "Company", "Quantity", "BuyPrice", "BuyDate"])
        
        if self.portfolio.empty:
            self.portfolio = new_row
        else:
            self.portfolio = pd.concat([self.portfolio, new_row], ignore_index=True)
            
        self.save_portfolio()
        
        # Clear inputs
        self.symbol_entry.delete(0, 'end')
        
        self.company_entry.configure(state="normal")
        self.company_entry.delete(0, 'end')
        self.company_entry.configure(state="disabled")
        
        self.quantity_entry.delete(0, 'end')
        self.price_entry.delete(0, 'end')
        self.buy_date_entry.delete(0, 'end')

    def delete_row(self, index):
        if messagebox.askyesno("Eliminar", "¿Seguro que deseas eliminar esta posición?"):
            self.portfolio = self.portfolio.drop(index).reset_index(drop=True)
            self.save_portfolio()
            
    def edit_position(self, index):
        row = self.portfolio.iloc[index]
        EditPositionDialog(self, row, lambda q, p, d: self.save_edited_position(index, q, p, d))
        
    def save_edited_position(self, index, quantity, price, date):
        self.portfolio.at[index, "Quantity"] = quantity
        self.portfolio.at[index, "BuyPrice"] = price
        self.portfolio.at[index, "BuyDate"] = date
        self.save_portfolio()

    def remove_position(self):
        pass # Deprecated

    def start_market_update(self):
        if self.portfolio.empty:
            return
        
        self.update_button.configure(state="disabled", text="Actualizando...")
        thread = threading.Thread(target=self.fetch_market_data)
        thread.start()

    def fetch_market_data(self):
        try:
            symbols = self.portfolio["Symbol"].unique().tolist()
            if not symbols:
                return

            tickers = yf.Tickers(" ".join(symbols))
            current_prices = {}
            
            for symbol in symbols:
                try:
                    # Access the ticker securely
                    ticker = tickers.tickers[symbol] if len(symbols) > 1 else tickers
                    # Fast fetch
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        current_prices[symbol] = hist["Close"].iloc[-1]
                    else:
                        current_prices[symbol] = 0
                except Exception as e:
                    print(f"Failed to fetch {symbol}: {e}")
                    current_prices[symbol] = 0

            # Update dataframe safely
            self.portfolio["CurrentPrice"] = self.portfolio["Symbol"].map(current_prices).fillna(0)
            
            # Schedule UI update on main thread
            self.after(0, self.update_ui_after_fetch)
            
        except Exception as e:
            print(f"Error fetching data: {e}")
        finally:
            self.after(0, lambda: self.update_button.configure(state="normal", text="Actualizar Datos"))

    def update_ui_after_fetch(self):
        self.save_portfolio() # Save the fetched prices too if we want, or just re-render
        self.update_ui()

    def update_ui(self):
        # Calculation
        if "CurrentPrice" not in self.portfolio.columns:
            self.portfolio["CurrentPrice"] = 0.0

        self.portfolio["Value"] = self.portfolio["Quantity"] * self.portfolio["CurrentPrice"]
        self.portfolio["Invested"] = self.portfolio["Quantity"] * self.portfolio["BuyPrice"]
        self.portfolio["ProfitLoss"] = self.portfolio["Value"] - self.portfolio["Invested"]

        total_invested = self.portfolio["Invested"].sum()
        total_value = self.portfolio["Value"].sum()
        total_pl = self.portfolio["ProfitLoss"].sum()
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

        # Update Cards
        self.card_total_invested.configure(text=f"${total_invested:,.2f}")
        self.card_current_value.configure(text=f"${total_value:,.2f}")
        color = "green" if total_pl >= 0 else "red"
        self.card_profit_loss.configure(text=f"${total_pl:,.2f} ({total_pl_pct:.2f}%)", text_color=color)

        # Update Table
        # clear existing rows and widget cache
        self.row_widgets = {}
        for widget in self.table_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0: # Skip header
                widget.destroy()

        for index, row in self.portfolio.iterrows():
            r = index + 1
            self.row_widgets[index] = []
            
            # Helper to bind click event
            def open_edit(event, i=index):
                self.edit_position(i)
            
            # Helper for hover
            def on_enter(event, i=index):
                self.on_row_hover(i, True)
            
            def on_leave(event, i=index):
                self.on_row_hover(i, False)
            
            # Create labels and bind click/hover
            # List of (text, color) tuples to make loop cleaner
            pl_color = "green" if row['ProfitLoss'] >= 0 else "red"
            comp_name = str(row.get("Company", ""))
            if len(comp_name) > 20: comp_name = comp_name[:20] + "..."
            
            lbl_configs = [
                (str(row["Symbol"]), "white"),
                (comp_name, "white"),
                (f"{row['Quantity']:.2f}", "white"),
                (f"${row['BuyPrice']:.2f}", "white"),
                (str(row.get('BuyDate', '')), "white"),
                (f"${row['CurrentPrice']:.2f}", "white"),
                (f"${row['Value']:.2f}", "white"),
                (f"${row['ProfitLoss']:.2f}", pl_color)
            ]

            for col_idx, (text_val, txt_color) in enumerate(lbl_configs):
                lbl = ctk.CTkLabel(self.table_frame, text=text_val, text_color=txt_color, corner_radius=5)
                lbl.grid(row=r, column=col_idx, padx=5, pady=2, sticky="ew")
                
                # Bindings
                lbl.bind("<Button-1>", open_edit)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)
                
                self.row_widgets[index].append(lbl)

            # Delete Button
            # We use a closure or default arg to capture the current index
            del_btn = ctk.CTkButton(self.table_frame, text="X", width=30, fg_color="red", hover_color="darkred",
                                    command=lambda i=index: self.delete_row(i))
            del_btn.grid(row=r, column=8, padx=5, pady=2)
    
    def on_row_hover(self, index, is_hover):
        color = "#333333" if is_hover else "transparent"
        if index in self.row_widgets:
            for widget in self.row_widgets[index]:
                try:
                    widget.configure(fg_color=color)
                except:
                    pass

        # Update Chart
        self.update_chart()

    def update_chart(self):
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if self.portfolio.empty:
            return

        # Prepare Data
        fig, ax = plt.subplots(figsize=(6, 1.2), dpi=100)
        fig.patch.set_facecolor('#2b2b2b') # Match dark theme background
        ax.set_facecolor('#2b2b2b')
        
        colors = ['g' if x >= 0 else 'r' for x in self.portfolio["ProfitLoss"]]
        bars = ax.bar(self.portfolio["Symbol"], self.portfolio["ProfitLoss"], color=colors)
        
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.set_title("Ganancia/Pérdida por Activo", color='white')
        
        # Embed in Tkinter
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        plt.close(fig)

if __name__ == "__main__":
    app = StockTrackerApp()
    app.mainloop()
