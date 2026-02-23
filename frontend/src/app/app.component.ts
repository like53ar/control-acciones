import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService, PortfolioResponse } from './portfolio.service';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import Chart from 'chart.js/auto';
import ChartDataLabels from 'chartjs-plugin-datalabels';

Chart.register(ChartDataLabels);

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './app.component.html'
})
export class AppComponent implements OnInit, OnDestroy, AfterViewInit {
    title = 'Portafolio Zen';
    @ViewChild('tickerContainer', { static: true }) tickerContainer!: ElementRef;

    portfolioData: PortfolioResponse | null = null;
    loading = true;
    currentDate = new Date();
    isUpdatingData = false;

    // Resumen Agrupado
    groupedAssets: any[] = [];

    getDaysElapsed(buyDate: string): string | number {
        if (!buyDate) return '-';
        const buy = new Date(buyDate).getTime();
        const now = new Date().getTime();
        const diffDays = Math.floor((now - buy) / (1000 * 60 * 60 * 24));
        return diffDays;
    }

    // Tipo de Cambio
    exchangeRate: number | null = null;
    loadingExchange = false;
    exchangeRateLastUpdated: string | null = null;
    isExchangeRateOutdated: boolean = false;
    private exchangeInterval: any;

    // Formulario de Inversión
    newItem = {
        symbol: '',
        company: '',
        quantity: null as number | null,
        buy_price: null as number | null,
        buy_date: new Date().toISOString().split('T')[0] // Default to today
    };
    submitting = false;
    loadingCompany = false;

    private symbolSubject = new Subject<string>();
    private symbolSubscription!: Subscription;

    constructor(private portfolioService: PortfolioService) { }

    ngOnInit() {
        this.fetchData();
        this.fetchExchangeRate();

        this.exchangeInterval = setInterval(() => {
            this.fetchExchangeRate();
            this.checkExchangeRateOutdated();
        }, 1200000); // Actualizar y chequear cada 20 minutos

        // Listener para buscar el nombre de la empresa sin saturar la API
        this.symbolSubscription = this.symbolSubject.pipe(
            debounceTime(500),
            distinctUntilChanged()
        ).subscribe(symbol => {
            if (symbol && symbol.trim().length > 0) {
                this.loadingCompany = true;
                this.portfolioService.getQuote(symbol).subscribe({
                    next: (res) => {
                        this.newItem.company = res.company;
                        this.loadingCompany = false;
                    },
                    error: () => {
                        this.newItem.company = '';
                        this.loadingCompany = false;
                    }
                });
            } else {
                this.newItem.company = '';
            }
        });
    }

    ngOnDestroy() {
        if (this.symbolSubscription) {
            this.symbolSubscription.unsubscribe();
        }
        if (this.exchangeInterval) {
            clearInterval(this.exchangeInterval);
        }
    }

    ngAfterViewInit() {
        if (this.tickerContainer) {
            const symbolsList = [
                { "description": "S&P 500", "proName": "FOREXCOM:SPXUSD" },
                { "description": "Nasdaq 100", "proName": "FOREXCOM:NSXUSD" },
                { "description": "Dow Jones", "proName": "FOREXCOM:DJI" },
                { "description": "Russell 2000", "proName": "AMEX:IWM" },
                { "description": "Merval", "proName": "BCBA:IMV" },
                { "description": "Nikkei 225", "proName": "JP225" },
                { "description": "DAX", "proName": "XETR:DAX" },
                { "description": "Soja", "proName": "ZS" },
                { "description": "Trigo", "proName": "ZW" },
                { "description": "Maíz", "proName": "ZC" },
                { "description": "Café", "proName": "KC" },
                { "description": "Cacao", "proName": "CC" },
                { "description": "Azúcar", "proName": "SB" },
                { "description": "Jugo de Naranja", "proName": "OJ" },
                { "description": "Petróleo WTI", "proName": "CL" },
                { "description": "Petróleo Brent", "proName": "BZ" },
                { "description": "Gas Natural", "proName": "NG" },
                { "description": "Gasolina", "proName": "RB" },
                { "description": "Aceite Calefacción", "proName": "HO" },
                { "description": "Carbón", "proName": "MTF" },
                { "description": "USD/MXN", "proName": "OANDA:USDMXN" },
                { "description": "USD/BRL", "proName": "FX_IDC:USDBRL" },
                { "description": "USD/ZAR", "proName": "OANDA:USDZAR" },
                { "description": "USD/TRY", "proName": "OANDA:USDTRY" },
                { "description": "USD/SGD", "proName": "OANDA:USDSGD" },
                { "description": "USD/NOK", "proName": "OANDA:USDNOK" },
                { "description": "USD/HKD", "proName": "OANDA:USDHKD" },
                { "description": "USD/CAD", "proName": "OANDA:USDCAD" },
                { "description": "EUR/USD", "proName": "OANDA:EURUSD" },
                { "description": "EUR/GBP", "proName": "OANDA:EURGBP" },
                { "description": "EUR/TRY", "proName": "OANDA:EURTRY" },
                { "description": "Oro", "proName": "OANDA:XAUUSD" },
                { "description": "Petróleo", "proName": "TVC:USOIL" },
                { "description": "Plata", "proName": "OANDA:XAGUSD" },
                { "description": "BTC", "proName": "BINANCE:BTCUSDT" },
                { "description": "ETH", "proName": "BINANCE:ETHUSDT" },
                { "description": "SOL", "proName": "BINANCE:SOLUSDT" },
                { "description": "XRP", "proName": "BINANCE:XRPUSDT" },
                { "description": "ADA", "proName": "BINANCE:ADAUSDT" },
                { "description": "Globant", "proName": "NYSE:GLOB" },
                { "description": "Vista Energy", "proName": "NYSE:VIST" },
                { "description": "Edenor", "proName": "NYSE:EDN" },
                { "description": "YPF", "proName": "NYSE:YPF" },
                { "description": "Apple", "proName": "NASDAQ:AAPL" },
                { "description": "Microsoft", "proName": "NASDAQ:MSFT" },
                { "description": "Nvidia", "proName": "NASDAQ:NVDA" },
                { "description": "Amazon", "proName": "NASDAQ:AMZN" },
                { "description": "Meta", "proName": "NASDAQ:META" },
                { "description": "Alphabet A", "proName": "NASDAQ:GOOGL" },
                { "description": "Alphabet C", "proName": "NASDAQ:GOOG" },
                { "description": "Berkshire", "proName": "NYSE:BRK.B" },
                { "description": "Eli Lilly", "proName": "NYSE:LLY" },
                { "description": "Broadcom", "proName": "NASDAQ:AVGO" },
                { "description": "Tesla", "proName": "NASDAQ:TSLA" },
                { "description": "JPMorgan", "proName": "NYSE:JPM" },
                { "description": "UnitedHealth", "proName": "NYSE:UNH" },
                { "description": "Visa", "proName": "NYSE:V" },
                { "description": "Exxon", "proName": "NYSE:XOM" },
                { "description": "Mastercard", "proName": "NYSE:MA" },
                { "description": "Costco", "proName": "NASDAQ:COST" },
                { "description": "Home Depot", "proName": "NYSE:HD" },
                { "description": "P&G", "proName": "NYSE:PG" },
                { "description": "Netflix", "proName": "NASDAQ:NFLX" },
                { "description": "J&J", "proName": "NYSE:JNJ" },
                { "description": "AbbVie", "proName": "NYSE:ABBV" },
                { "description": "Bank of America", "proName": "NYSE:BAC" },
                { "description": "Salesforce", "proName": "NYSE:CRM" },
                { "description": "Walmart", "proName": "WMT" },
                { "description": "Chevron", "proName": "NYSE:CVX" },
                { "description": "Coca-Cola", "proName": "NYSE:KO" },
                { "description": "Merck", "proName": "NYSE:MRK" },
                { "description": "PepsiCo", "proName": "NASDAQ:PEP" },
                { "description": "Oracle", "proName": "NYSE:ORCL" },
                { "description": "Adobe", "proName": "NASDAQ:ADBE" },
                { "description": "Thermo Fisher", "proName": "NYSE:TMO" },
                { "description": "Linde", "proName": "NASDAQ:LIN" },
                { "description": "McDonald's", "proName": "NYSE:MCD" },
                { "description": "Cisco", "proName": "NASDAQ:CSCO" },
                { "description": "Abbott", "proName": "NYSE:ABT" },
                { "description": "Accenture", "proName": "NYSE:ACN" },
                { "description": "GE Aerospace", "proName": "NYSE:GE" },
                { "description": "Caterpillar", "proName": "NYSE:CAT" },
                { "description": "Danaher", "proName": "NYSE:DHR" },
                { "description": "Verizon", "proName": "NYSE:VZ" },
                { "description": "Intuit", "proName": "NASDAQ:INTU" },
                { "description": "Qualcomm", "proName": "NASDAQ:QCOM" },
                { "description": "IBM", "proName": "NYSE:IBM" },
                { "description": "Texas Instr", "proName": "NASDAQ:TXN" },
                { "description": "Applied Mat", "proName": "NASDAQ:AMAT" },
                { "description": "Amgen", "proName": "NASDAQ:AMGN" },
                { "description": "Pfizer", "proName": "NYSE:PFE" },
                { "description": "Intel", "proName": "NASDAQ:INTC" },
                { "description": "Goldman Sachs", "proName": "NYSE:GS" }
            ];

            // Mezclar el array aleatoriamente para que comience en distintos activos cada vez
            for (let i = symbolsList.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [symbolsList[i], symbolsList[j]] = [symbolsList[j], symbolsList[i]];
            }

            const script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js';
            script.async = true;
            script.innerHTML = JSON.stringify({
                "symbols": symbolsList,
                "showSymbolLogo": true,
                "isTransparent": true,
                "displayMode": "adaptive",
                "colorTheme": "dark",
                "locale": "es"
            });
            this.tickerContainer.nativeElement.appendChild(script);
        }
    }

    onSymbolChange(value: string) {
        this.symbolSubject.next(value);
    }

    fetchData() {
        if (!this.portfolioData) {
            this.loading = true; // Solo mostrar esqueleto de carga la primera vez
        }
        this.isUpdatingData = true;
        this.portfolioService.getPortfolio().subscribe({
            next: (data) => {
                this.portfolioData = data;
                this.processGroupedAssets(data.data);
                this.loading = false;
                this.isUpdatingData = false;
            },
            error: (err) => {
                console.error('Error al obtener portafolio', err);
                this.loading = false;
                this.isUpdatingData = false;
            }
        });
    }

    fetchExchangeRate() {
        this.loadingExchange = true;
        this.portfolioService.getExchangeRate().subscribe({
            next: (data) => {
                this.exchangeRate = data.price;
                this.exchangeRateLastUpdated = data.last_updated;
                this.checkExchangeRateOutdated();
                this.loadingExchange = false;
            },
            error: (err) => {
                console.error('Error al obtener tipo de cambio', err);
                this.loadingExchange = false;
            }
        });
    }

    checkExchangeRateOutdated() {
        if (!this.exchangeRateLastUpdated) {
            this.isExchangeRateOutdated = false;
            return;
        }

        let dateStr = this.exchangeRateLastUpdated;
        // Compatibilidad con formato antiguo "2026-02-19 17:56:35" -> "2026-02-19T17:56:35Z"
        if (dateStr.includes(' ') && !dateStr.includes('T')) {
            dateStr = dateStr.replace(' ', 'T') + 'Z';
        }

        const lastUpdated = new Date(dateStr).getTime();
        const now = new Date().getTime();
        const diffMinutes = (now - lastUpdated) / (1000 * 60);

        this.isExchangeRateOutdated = diffMinutes > 20;
    }

    processGroupedAssets(assets: any[]) {
        const grouped = new Map<string, any>();

        for (const item of assets) {
            const sym = item.Symbol;
            const quantity = parseFloat(item.Quantity) || 0;
            const currentPrice = parseFloat(item.CurrentPrice) || 0;
            const value = quantity * currentPrice;

            if (grouped.has(sym)) {
                const existing = grouped.get(sym);
                existing.Quantity += quantity;
                existing.CurrentValue += value;
            } else {
                grouped.set(sym, {
                    Symbol: sym,
                    Company: item.Company,
                    Quantity: quantity,
                    CurrentPrice: currentPrice,
                    CurrentValue: value
                });
            }
        }

        // Convertimos el Map en un Array y lo ordenamos por Valor Total Descendente
        this.groupedAssets = Array.from(grouped.values()).sort((a, b) => b.CurrentValue - a.CurrentValue);
    }

    addItem() {
        if (!this.newItem.symbol || !this.newItem.quantity || !this.newItem.buy_price) {
            alert('Por favor, completa todos los campos requeridos para añadir tu inversión.');
            return;
        }

        this.submitting = true;

        // Formatear payload para enviarlo al backend
        const payload: any = {
            symbol: this.newItem.symbol,
            quantity: this.newItem.quantity,
            buy_price: this.newItem.buy_price
        };

        if (this.newItem.company) payload.company = this.newItem.company;
        if (this.newItem.buy_date) payload.buy_date = this.newItem.buy_date;

        this.portfolioService.addPortfolioItem(payload).subscribe({
            next: () => {
                this.newItem = {
                    symbol: '',
                    company: '',
                    quantity: null,
                    buy_price: null,
                    buy_date: new Date().toISOString().split('T')[0]
                };
                this.submitting = false;
                this.fetchData();
            },
            error: (err) => {
                console.error('Error al añadir posición', err);
                alert('Hubo un error al conectarse con el servidor para guardar la posición.');
                this.submitting = false;
            }
        });
    }

    // Modal de Confirmación
    showDeleteModal = false;
    itemToDelete: any = null;
    isDeleting = false;

    confirmDelete(item: any) {
        this.itemToDelete = item;
        this.showDeleteModal = true;
    }

    cancelDelete() {
        this.showDeleteModal = false;
        this.itemToDelete = null;
    }

    executeDelete() {
        if (!this.itemToDelete) return;

        this.isDeleting = true;
        this.portfolioService.deletePortfolioItem(this.itemToDelete.id).subscribe({
            next: () => {
                // Refresco "silencioso" para no hacer titilar toda la página
                this.portfolioService.getPortfolio().subscribe(data => {
                    this.portfolioData = data;
                    this.isDeleting = false;
                    this.showDeleteModal = false;
                    this.itemToDelete = null;
                });
            },
            error: (err) => {
                console.error('Error al eliminar posición', err);
                this.isDeleting = false;
                this.showDeleteModal = false;
                this.itemToDelete = null;
            }
        });
    }

    // Modal de Venta
    showSellModal = false;
    itemToSell: any = null;
    isSelling = false;
    sellPrice: number | null = null;
    sellDate: string = new Date().toISOString().split('T')[0];

    // Modal de Edición
    showEditModal = false;
    itemToEditOrig: any = null;
    isEditing = false;
    editItemData = {
        symbol: '',
        company: '',
        quantity: null as number | null,
        buy_price: null as number | null,
        buy_date: ''
    };

    // Modal de Gráfico de Torta
    showChartModal = false;
    portfolioChart: any;

    confirmSell(item: any) {
        this.itemToSell = item;
        this.sellPrice = item.CurrentPrice;
        this.sellDate = new Date().toISOString().split('T')[0];
        this.showSellModal = true;
    }

    cancelSell() {
        this.showSellModal = false;
        this.itemToSell = null;
    }

    executeSell() {
        if (!this.itemToSell || !this.sellPrice || !this.sellDate) return;

        this.isSelling = true;
        this.portfolioService.sellPortfolioItem(this.itemToSell.id, {
            sell_price: this.sellPrice,
            sell_date: this.sellDate
        }).subscribe({
            next: () => {
                this.portfolioService.getPortfolio().subscribe(data => {
                    this.portfolioData = data;
                    this.isSelling = false;
                    this.showSellModal = false;
                    this.itemToSell = null;
                });
            },
            error: (err) => {
                console.error('Error al vender posición', err);
                this.isSelling = false;
            }
        });
    }

    // Modal de Edición Methods
    confirmEdit(item: any) {
        this.itemToEditOrig = item;
        this.editItemData = {
            symbol: item.Symbol,
            company: item.Company,
            quantity: item.Quantity,
            buy_price: item.BuyPrice,
            buy_date: item.BuyDate || ''
        };
        this.showEditModal = true;
    }

    cancelEdit() {
        this.showEditModal = false;
        this.itemToEditOrig = null;
    }

    executeEdit() {
        if (!this.itemToEditOrig || !this.editItemData.symbol || !this.editItemData.quantity || !this.editItemData.buy_price) {
            return;
        }

        this.isEditing = true;
        const payload: any = {
            symbol: this.editItemData.symbol,
            quantity: this.editItemData.quantity,
            buy_price: this.editItemData.buy_price,
            company: this.editItemData.company,
            buy_date: this.editItemData.buy_date
        };

        this.portfolioService.updatePortfolioItem(this.itemToEditOrig.id, payload).subscribe({
            next: () => {
                this.portfolioService.getPortfolio().subscribe(data => {
                    this.portfolioData = data;
                    this.isEditing = false;
                    this.showEditModal = false;
                    this.itemToEditOrig = null;
                });
            },
            error: (err) => {
                console.error('Error al editar posición', err);
                alert('Ocurrió un error al guardar los cambios.');
                this.isEditing = false;
            }
        });
    }

    // Modal de Gráfico de Torta Methods
    openChartModal() {
        this.showChartModal = true;

        // Wait for modal to render the canvas
        setTimeout(() => {
            const ctx = document.getElementById('portfolioPieChart') as HTMLCanvasElement;
            if (!ctx) return;

            // Prepare data from groupedAssets
            const sortedAssets = [...this.groupedAssets].sort((a, b) => b.CurrentValue - a.CurrentValue);
            const labels = sortedAssets.map(a => a.Symbol);
            const data = sortedAssets.map(a => a.CurrentValue);

            const backgroundColors = [
                '#38bdf8', '#818cf8', '#f472b6', '#34d399', '#fbbf24',
                '#f87171', '#a78bfa', '#2dd4bf', '#fb923c', '#9ca3af'
            ];

            if (this.portfolioChart) {
                this.portfolioChart.destroy();
            }

            this.portfolioChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderWidth: 1,
                        borderColor: '#1e293b'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        datalabels: {
                            formatter: (value: any, ctx: any) => {
                                let sum = 0;
                                let dataArr = ctx.chart.data.datasets[0].data;
                                dataArr.map((data: number) => {
                                    sum += data;
                                });
                                let percentage = (value * 100 / sum).toFixed(1) + "%";
                                // Hide labels for very small slices (e.g. < 3%)
                                if ((value * 100 / sum) < 3) return null;
                                return percentage;
                            },
                            color: '#fff',
                            font: {
                                weight: 'bold',
                                size: 12,
                                family: "'Inter', sans-serif"
                            },
                            textStrokeColor: 'rgba(0,0,0,0.5)',
                            textStrokeWidth: 1
                        },
                        legend: {
                            position: 'right',
                            labels: {
                                color: '#cbd5e1',
                                font: {
                                    family: "'Inter', sans-serif",
                                    size: 11
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context: any) {
                                    let label = context.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed !== null) {
                                        label += new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(context.parsed);
                                    }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        }, 50);
    }

    closeChartModal() {
        this.showChartModal = false;
        if (this.portfolioChart) {
            this.portfolioChart.destroy();
            this.portfolioChart = null;
        }
    }

    // Exportar a CSV
    exportToCSV() {
        if (!this.portfolioData || !this.portfolioData.data || this.portfolioData.data.length === 0) {
            alert('No hay datos para exportar.');
            return;
        }

        const headers = ['Activo', 'Empresa', 'Cantidad', 'Precio Compra', 'Precio Actual', 'Total Invertido', 'Valor Actual', 'Ganancia', 'Fecha Compra'];

        // Escape helper for CSV cells
        const escapeCSV = (field: any) => {
            if (field === null || field === undefined) return '';
            const str = String(field);
            // Si tiene comas, comillas dobles o saltos de línea, lo envolvemos en comillas y escapamos las comillas internas
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        };

        const rows = this.portfolioData.data.map(item => [
            escapeCSV(item.Symbol),
            escapeCSV(item.Company),
            escapeCSV(item.Quantity),
            escapeCSV(item.BuyPrice),
            escapeCSV(item.CurrentPrice),
            escapeCSV(item.TotalInvested),
            escapeCSV(item.CurrentTotal),
            escapeCSV(item.Gain),
            escapeCSV(item.BuyDate || '')
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        // Agregar BOM para que Excel detecte UTF-8 correctamente (acentos y caracteres especiales)
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');

        const now = new Date();
        const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD

        link.setAttribute('href', url);
        link.setAttribute('download', `portafolio_zen_${dateStr}.csv`);
        document.body.appendChild(link);
        link.click();

        // Limpiar
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}
